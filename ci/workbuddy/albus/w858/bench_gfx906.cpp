// W858 C 线：gfx906 (MI50) 微基准 —— 判 G8(LDS padding) / G9(DPP) / G10(fp16 dot) / R13(int8) 值不值得做。
//
// 只量"上限"，不量我们的 kernel：
//   1) HBM 读带宽                 —— gather / blob 拷贝的地板
//   2) LDS 带宽 无冲突 vs 32 路冲突 —— padding 的收益上限（G8）
//   3) fp32 FMA / fp16 packed FMA  —— 标量算力
//   4) int8 v_dot4 吞吐            —— MMQ 的 int8 上限（决定 R13 与 dp4a 路线）
//
// 编译：hipcc -O3 --offload-arch=gfx906 bench_gfx906.cpp -o bench
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <chrono>
#include <cstdio>
#include <vector>

#define CK(x) do { hipError_t e_ = (x); if (e_ != hipSuccess) { \
  printf("ERR %s -> %s\n", #x, hipGetErrorString(e_)); return 1; } } while (0)

static double now_ms() {
  return (double) std::chrono::duration_cast<std::chrono::microseconds>(
             std::chrono::steady_clock::now().time_since_epoch()).count() / 1000.0;
}

// ---------------------------------------------------------------- 1 HBM 读带宽
__global__ void k_bwread(const float4* __restrict__ p, size_t n4, float* out) {
  size_t i = blockIdx.x * (size_t) blockDim.x + threadIdx.x;
  size_t stride = (size_t) gridDim.x * blockDim.x;
  float4 acc = make_float4(0, 0, 0, 0);
  for (; i < n4; i += stride) {
    float4 v = p[i];
    acc.x += v.x; acc.y += v.y; acc.z += v.z; acc.w += v.w;
  }
  if (acc.x == 12345.678f) out[0] = acc.x + acc.y + acc.z + acc.w;
}

// ---------------------------------------------------------------- 2 LDS 带宽
// mode 0: 连续（无冲突）   mode 1: 全 wave 打同一个 bank（32 路冲突）
__global__ void k_lds(int mode, int iters, float* out) {
  extern __shared__ float s[];
  const int tid = threadIdx.x;
  const int n = 64 * 40;
  for (int i = tid; i < n; i += blockDim.x) s[i] = (float) i;
  __syncthreads();
  float acc = 0.f;
  if (mode == 0) {
    for (int i = 0; i < iters; ++i) acc += s[((i & 31) << 6) + tid];
  } else {
    const int off = (tid & 63) * 32;
    for (int i = 0; i < iters; ++i) acc += s[off + (i & 7)];
  }
  if (acc == 12345.678f) out[0] = acc;
}

// ---------------------------------------------------------------- 3 fp32 FMA
// 4 条独立链：FMA 延迟 ~4 cycle，链条数必须 >= 延迟才能到峰值
__global__ void k_fma32(int iters, float* out) {
  float a0 = threadIdx.x * 1e-7f, a1 = a0 + 1e-6f, a2 = a0 + 2e-6f, a3 = a0 + 3e-6f;
  const float b = 1.0000001f, k = 1e-7f;
  for (int i = 0; i < iters; ++i) {
    a0 = fmaf(a0, b, k); a1 = fmaf(a1, b, k); a2 = fmaf(a2, b, k); a3 = fmaf(a3, b, k);
  }
  if (a0 == 12345.678f) out[0] = a0 + a1 + a2 + a3;
}

// ---------------------------------------------------------------- 3b fp16 packed FMA
__global__ void k_fma16(int iters, float* out) {
  // 必须让输入依赖 threadIdx，否则编译器会把整条链常量折叠掉（第一次实测就是这样归零的）
  const float t = threadIdx.x * 1e-7f;
  __half2 a0 = __float2half2_rn(t), a1 = __float2half2_rn(t + 1e-6f);
  __half2 a2 = __float2half2_rn(t + 2e-6f), a3 = __float2half2_rn(t + 3e-6f);
  const __half2 b = __float2half2_rn(1.0001f), k = __float2half2_rn(1e-7f);
  for (int i = 0; i < iters; ++i) {
    a0 = __hfma2(a0, b, k); a1 = __hfma2(a1, b, k);
    a2 = __hfma2(a2, b, k); a3 = __hfma2(a3, b, k);
  }
  float2 f = __half22float2(__hadd2(__hadd2(a0, a1), __hadd2(a2, a3)));
  if (f.x == 12345.678f) out[0] = f.x;
}

// ---------------------------------------------------------------- 4 int8 dot4
__global__ void k_dot4(int iters, int* out) {
  int a = (int) (threadIdx.x * 0x01010101u) | 0x01010101;
  int b = a ^ 0x03030303;
  int c0 = 0, c1 = 1, c2 = 2, c3 = 3;              // 4 条独立累加链
  for (int i = 0; i < iters; ++i) {
    c0 = __builtin_amdgcn_sdot4(a, b, c0, false); c1 = __builtin_amdgcn_sdot4(a, b, c1, false);
    c2 = __builtin_amdgcn_sdot4(a, b, c2, false); c3 = __builtin_amdgcn_sdot4(a, b, c3, false);
  }
  int acc = c0 + c1 + c2 + c3;
  if (acc == 12345) out[0] = acc;
}

int main() {
  hipDeviceProp_t prop;
  CK(hipGetDeviceProperties(&prop, 0));
  const double spec_bw = prop.memoryClockRate / 1e6 * (prop.memoryBusWidth / 8.0) * 2.0;
  printf("dev=%s  CUs=%d  clock=%.2f GHz  bus=%d bit  spec HBM=%.0f GB/s  wave=%d\n",
         prop.name, prop.multiProcessorCount, prop.clockRate / 1e6,
         prop.memoryBusWidth, spec_bw, prop.warpSize);
  const int SM = prop.multiProcessorCount;
  const int BLK = 256, GRID = SM * 16;
  float* d_out = nullptr; int* d_iout = nullptr;
  CK(hipMalloc(&d_out, 4096)); CK(hipMalloc(&d_iout, 4096));

  // ---- 1 HBM
  {
    size_t n4 = (size_t) 512 * 1024 * 1024 / 16;
    float4* d = nullptr;
    CK(hipMalloc(&d, n4 * 16)); CK(hipMemset(d, 1, n4 * 16));
    for (int r = 0; r < 3; ++r) {
      double t0 = now_ms();
      k_bwread<<<GRID, BLK>>>(d, n4, d_out);
      CK(hipDeviceSynchronize());
      double ms = now_ms() - t0;
      printf("HBM read  : %7.1f GB/s   (%.3f ms / 512 MB)\n", n4 * 16.0 / (ms * 1e6), ms);
    }
    hipFree(d);
  }

  // ---- 2 LDS
  {
    const int iters = 200000;
    const int ldsize = 64 * 40 * 4;
    for (int mode = 0; mode < 2; ++mode) {
      double t0 = now_ms();
      k_lds<<<GRID, 64, ldsize>>>(mode, iters, d_out);
      CK(hipDeviceSynchronize());
      double ms = now_ms() - t0;
      double bytes = (double) GRID * 64 * iters * 4.0;
      printf("LDS %s : %7.1f GB/s   (%.3f ms)\n", mode == 0 ? "noconf" : "32-way", bytes / (ms * 1e6), ms);
    }
  }

  // ---- 3 标量算力
  {
    const int iters = 200000;
    double t0 = now_ms();
    k_fma32<<<GRID, BLK>>>(iters, d_out); CK(hipDeviceSynchronize());
    double ms = now_ms() - t0;
    printf("fp32 FMA  : %7.1f TFLOPS (%.3f ms)  [peak 13.3]\n", (double) GRID * BLK * iters * 4 * 2 / (ms * 1e9), ms);

    t0 = now_ms();
    k_fma16<<<GRID, BLK>>>(iters, d_out); CK(hipDeviceSynchronize());
    ms = now_ms() - t0;
    printf("fp16 pkFMA: %7.1f TFLOPS (%.3f ms)  [peak 26.6]\n", (double) GRID * BLK * iters * 4 * 4 / (ms * 1e9), ms);
  }

  // ---- 4 int8 dot4
  {
    const int iters = 200000;
    double t0 = now_ms();
    k_dot4<<<GRID, BLK>>>(iters, d_iout); CK(hipDeviceSynchronize());
    double ms = now_ms() - t0;
    printf("int8 dot4 : %7.1f TOPS   (%.3f ms)\n", (double) GRID * BLK * iters * 8 / (ms * 1e9), ms);
  }

  hipFree(d_out); hipFree(d_iout);
  return 0;
}
