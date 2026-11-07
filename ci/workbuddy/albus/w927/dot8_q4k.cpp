// 验证：Q4_K 的 u4 权重能否用 v_dot8_i32_i4 算，且只需一个可预计算的修正项
//
// 数学：
//   a_u4 ∈ [0,15],  a_i4 = a_u4 - 8  ⇔  a_i4_bits = a_u4 ^ 0x8   (4-bit 补码偏移)
//   sum(a_u4 * b_i4) = dot8(a_u4 ^ 0x8, b_i4) + 8 * sum(b_i4)
//                     ^^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^
//                     一条指令                  b 的每组 8 元素和，可预计算
//
// 本程序用 gfx906 实测：(1) 三种算法互相印证；(2) 吞吐 dot8 vs dp4a。
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <random>

#define CK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
  printf("HIP error %s at %d: %s\n", #x, __LINE__, hipGetErrorString(e)); exit(1);} } while (0)

__device__ __forceinline__ int dot8(int a, int b, int c) {
    return __builtin_amdgcn_sdot8(a, b, c, false);
}
__device__ __forceinline__ int dp4a_i8(int a, int b, int c) {
    return __builtin_amdgcn_sdot4(a, b, c, false);
}

// 一个 dword 内 8 个 nibble（低半字节 = 偶数下标），值来自 Q4_K 的真实分布：0..15
__device__ int pack_u4(const uint8_t* v) {
    int r = 0;
    for (int i = 0; i < 8; ++i) r |= ((int)v[i] & 0xF) << (4 * i);
    return r;
}
__device__ int pack_i4_from_i8(const int8_t* v) {   // 4-bit 有符号打包（截断到 [-8,7]）
    int r = 0;
    for (int i = 0; i < 8; ++i) {
        int t = v[i] < -8 ? -8 : (v[i] > 7 ? 7 : v[i]);
        r |= (t & 0xF) << (4 * i);
    }
    return r;
}

// ---------- 正确性：三路对照 ----------
__global__ void k_check(const uint8_t* a_u4, const int8_t* b_i8, int* out_dp4a_ref,
                        int* out_dot8_fix, int* out_exact) {
    int A = pack_u4(a_u4);
    int B = pack_i4_from_i8(b_i8);

    // 1) 精确参考（整型手算，无硬件 dot）
    int exact = 0;
    for (int i = 0; i < 8; ++i) {
        int a = a_u4[i] & 0xF;
        int b = b_i8[i] < -8 ? -8 : (b_i8[i] > 7 ? 7 : b_i8[i]);
        exact += a * b;
    }

    // 2) dp4a 两次（低 4 + 高 4）：dp4a 吃 int8，需把 nibble 扩成 byte
    int lo = 0, hi = 0;
    for (int i = 0; i < 4; ++i) lo |= ((a_u4[i] & 0xF)) << (8 * i);
    for (int i = 0; i < 4; ++i) hi |= ((a_u4[i + 4] & 0xF)) << (8 * i);
    int blo = 0, bhi = 0;
    for (int i = 0; i < 4; ++i) blo |= ((b_i8[i] & 0xFF)) << (8 * i);
    for (int i = 0; i < 4; ++i) bhi |= ((b_i8[i + 4] & 0xFF)) << (8 * i);
    int r_dp4a = dp4a_i8(hi, bhi, dp4a_i8(lo, blo, 0));

    // 3) dot8 + 修正项：dot8(A^0x8, B) + 8 * sum(b)
    int xorA = A ^ 0x88888888;   // 每个 nibble 的 bit3，即 4-bit 补码的 +8/-8 偏移
    int sumb = 0;
    for (int i = 0; i < 8; ++i) sumb += (b_i8[i] < -8 ? -8 : (b_i8[i] > 7 ? 7 : b_i8[i]));
    int r_dot8 = dot8(xorA, B, 0) + 8 * sumb;

    out_exact[0] = exact;
    out_dp4a_ref[0] = r_dp4a;
    out_dot8_fix[0] = r_dot8;
}

// ---------- 吞吐：模拟真实 vec_dot 内层（含解包） ----------
template <int USE_DOT8>
__global__ void __launch_bounds__(256) k_bench(const int* __restrict__ w, const int* __restrict__ x,
                                               int iters, int* sink) {
    int acc = 0;
    int wv = w[threadIdx.x & 63];
    int xv = x[threadIdx.x & 63];
    for (int it = 0; it < iters; ++it) {
        int a = wv + it;   // 防常量折叠
#pragma unroll
        for (int j = 0; j < 8; ++j) {
            if (USE_DOT8) {
                acc = dot8(a ^ 0x88888888, xv, acc);
            } else {
                // 等价的两条 dp4a：低/高半字节各自扩成 byte（真实 MMQ 就是这么拆的）
                int lo = a & 0x0F0F0F0F;
                int hi = (a >> 4) & 0x0F0F0F0F;
                acc = dp4a_i8(hi, xv, dp4a_i8(lo, xv, acc));
            }
        }
    }
    if (acc == 12345678) sink[0] = acc;
}

int main() {
    printf("=== 1. 正确性：u4 权重 × i4 激活，dot8+修正 vs dp4a vs 精确 ===\n");
    {
        std::mt19937 rng(7);
        std::uniform_int_distribution<int> d4(0, 15), d8(-8, 7);
        uint8_t ha[8]; int8_t hb[8];
        for (int i = 0; i < 8; ++i) { ha[i] = (uint8_t)d4(rng); hb[i] = (int8_t)d8(rng); }

        uint8_t *da; int8_t *db; int *o1, *o2, *o3;
        CK(hipMalloc(&da, 8)); CK(hipMalloc(&db, 8));
        CK(hipMalloc(&o1, 4)); CK(hipMalloc(&o2, 4)); CK(hipMalloc(&o3, 4));
        CK(hipMemcpy(da, ha, 8, hipMemcpyHostToDevice));
        CK(hipMemcpy(db, hb, 8, hipMemcpyHostToDevice));
        k_check<<<1, 1>>>(da, db, o1, o2, o3);
        CK(hipDeviceSynchronize());
        int exact, r_dp4a, r_dot8;
        CK(hipMemcpy(&exact, o3, 4, hipMemcpyDeviceToHost));
        CK(hipMemcpy(&r_dp4a, o1, 4, hipMemcpyDeviceToHost));
        CK(hipMemcpy(&r_dot8, o2, 4, hipMemcpyDeviceToHost));
        printf("  a(u4) ="); for (int i = 0; i < 8; ++i) printf(" %2d", ha[i]);
        printf("\n  b(i4) ="); for (int i = 0; i < 8; ++i) printf(" %2d", hb[i]);
        printf("\n  exact=%d  dp4a(x2)=%d  dot8+fix=%d  -> %s\n", exact, r_dp4a, r_dot8,
               (exact == r_dp4a && exact == r_dot8) ? "ALL MATCH" : "MISMATCH");
    }

    printf("\n=== 2. 吞吐：8 元素一组，dot8 x1 vs dp4a x2（60 CU x 256 thr）===\n");
    {
        const int iters = 20000;
        int *w, *x, *sink;
        CK(hipMalloc(&w, 64 * 4)); CK(hipMalloc(&x, 64 * 4)); CK(hipMalloc(&sink, 4));
        hipMemset(w, 0x11, 64 * 4); hipMemset(x, 0x11, 64 * 4);

        hipEvent_t t0, t1; CK(hipEventCreate(&t0)); CK(hipEventCreate(&t1));
        const int blocks = 60, threads = 256, reps = 5;
        double macs = (double)blocks * threads * 4 * 2 * 8 * iters;   // 4 累加器 x 2 次 x 8 MAC

        for (int mode = 0; mode < 2; ++mode) {
            double best = 1e30;
            for (int r = 0; r < reps; ++r) {
                CK(hipEventRecord(t0));
                if (mode == 0) k_bench<1><<<blocks, threads>>>(w, x, iters, sink);
                else           k_bench<0><<<blocks, threads>>>(w, x, iters, sink);
                CK(hipEventRecord(t1)); CK(hipEventSynchronize(t1));
                float ms; CK(hipEventElapsedTime(&ms, t0, t1));
                if (ms < best) best = ms;
            }
            printf("  %-8s %7.3f ms  -> %.2f TMAC/s\n", mode == 0 ? "dot8x1" : "dp4a x2",
                   best, macs / (best * 1e9));
        }
    }
    printf("\n注：第 2 段是纯 ILP 微基准（不含 LDS/地址），只用来确认 8 元素一组时两者的指令数比。\n");
    return 0;
}
