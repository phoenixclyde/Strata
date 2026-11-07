// W1050 R114 microbench: gdn_ab shape (n=2560, rows=2*48), fp32-fmaf (production)
// vs fp16-dot2 (proposed B4).  Both read the same bf16 weights; the dot2 variant also
// pays on-the-fly bf16->fp16 + fp32->fp16 conversion.  If the site is memory-bound the
// two arms converge; if ALU-bound dot2 pulls ahead.  Roofline estimate: 1 MAC/byte vs
// gfx906 balance ~29 MAC/byte => memory-bound x29.
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cmath>

static inline float bf16_to_f32(uint16_t b) {
    union { uint32_t u; float f; } v; v.u = (uint32_t) b << 16; return v.f;
}

__global__ void ab_fmaf(const float* __restrict__ x, const uint16_t* __restrict__ wa,
                        const uint16_t* __restrict__ wb, float* __restrict__ out, int n) {
    const int row = blockIdx.x * 8 + (threadIdx.x >> 5), lane = threadIdx.x & 31;
    if (row >= 96) return;
    const uint16_t* w = row >= 48 ? wb : wa;
    const int r = row >= 48 ? row - 48 : row;
    const uint4* w4 = reinterpret_cast<const uint4*>(w + (size_t) r * n);
    float acc = 0.0f;
    for (int j = lane; j < n / 8; j += 32) {
        const uint4 wv = __ldg(w4 + j);
        const float4 xa = *reinterpret_cast<const float4*>(x + j * 8);
        const float4 xb = *reinterpret_cast<const float4*>(x + j * 8 + 4);
        acc = fmaf(__uint_as_float(wv.x << 16), xa.x, acc); acc = fmaf(__uint_as_float(wv.x & 0xffff0000u), xa.y, acc);
        acc = fmaf(__uint_as_float(wv.y << 16), xa.z, acc); acc = fmaf(__uint_as_float(wv.y & 0xffff0000u), xa.w, acc);
        acc = fmaf(__uint_as_float(wv.z << 16), xb.x, acc); acc = fmaf(__uint_as_float(wv.z & 0xffff0000u), xb.y, acc);
        acc = fmaf(__uint_as_float(wv.w << 16), xb.z, acc); acc = fmaf(__uint_as_float(wv.w & 0xffff0000u), xb.w, acc);
    }
    for (int o = 16; o > 0; o >>= 1) acc += __shfl_xor_sync(0xffffffffffffffffull, acc, o);
    if (lane == 0) out[row] = acc;
}

__device__ __forceinline__ float dot2(float acc, uint32_t a, uint32_t b) {
    // gfx906 v_dot2_f32_f16: dst, src0(acc), src1(packed 2xf16), src2(packed 2xf16)
    asm volatile("v_dot2_f32_f16 %0, %1, %2, %3" : "+v"(acc) : "v"(a), "v"(b));
    return acc;
}

__global__ void ab_dot2(const float* __restrict__ x, const uint16_t* __restrict__ wa,
                        const uint16_t* __restrict__ wb, float* __restrict__ out, int n) {
    const int row = blockIdx.x * 8 + (threadIdx.x >> 5), lane = threadIdx.x & 31;
    if (row >= 96) return;
    const uint16_t* w = row >= 48 ? wb : wa;
    const int r = row >= 48 ? row - 48 : row;
    const uint4* w4 = reinterpret_cast<const uint4*>(w + (size_t) r * n);
    float acc = 0.0f;
    for (int j = lane; j < n / 8; j += 32) {
        const uint4 wv = __ldg(w4 + j);
        const float4 xa = *reinterpret_cast<const float4*>(x + j * 8);
        const float4 xb = *reinterpret_cast<const float4*>(x + j * 8 + 4);
        // bf16 bits -> f32 -> f16 (on the fly; production KI preconverts for reuse)
        float wf[8];
        wf[0] = __uint_as_float(wv.x << 16);         wf[1] = __uint_as_float(wv.x & 0xffff0000u);
        wf[2] = __uint_as_float(wv.y << 16);         wf[3] = __uint_as_float(wv.y & 0xffff0000u);
        wf[4] = __uint_as_float(wv.z << 16);         wf[5] = __uint_as_float(wv.z & 0xffff0000u);
        wf[6] = __uint_as_float(wv.w << 16);         wf[7] = __uint_as_float(wv.w & 0xffff0000u);
        float xf[8] = {xa.x, xa.y, xa.z, xa.w, xb.x, xb.y, xb.z, xb.w};
        uint32_t wp[4], ap[4];
        for (int k = 0; k < 4; ++k) {
            __half2 wh = __halves2half2(__float2half(wf[2 * k]), __float2half(wf[2 * k + 1]));
            __half2 ah = __halves2half2(__float2half(xf[2 * k]), __float2half(xf[2 * k + 1]));
            wp[k] = *reinterpret_cast<uint32_t*>(&wh);
            ap[k] = *reinterpret_cast<uint32_t*>(&ah);
        }
        acc = dot2(acc, wp[0], ap[0]); acc = dot2(acc, wp[1], ap[1]);
        acc = dot2(acc, wp[2], ap[2]); acc = dot2(acc, wp[3], ap[3]);
    }
    for (int o = 16; o > 0; o >>= 1) acc += __shfl_xor_sync(0xffffffffffffffffull, acc, o);
    if (lane == 0) out[row] = acc;
}

int main() {
    const int N = 2560, ROWS = 96;
    float* x; uint16_t *wa, *wb; float* o1; float* o2;
    hipMalloc(&x, N * sizeof(float));
    hipMalloc(&wa, (size_t) N * 48 * 2);
    hipMalloc(&wb, (size_t) N * 48 * 2);
    hipMalloc(&o1, ROWS * 4);
    hipMalloc(&o2, ROWS * 4);
    float* hx = (float*) malloc(N * 4);
    uint16_t* hw = (uint16_t*) malloc((size_t) N * 48 * 2);
    srand(7);
    for (int i = 0; i < N; ++i) hx[i] = 0.25f * ((rand() % 2001) - 1000) / 1000.0f;
    for (size_t i = 0; i < (size_t) N * 48; ++i) {
        float v = 0.5f * ((rand() % 2001) - 1000) / 1000.0f;
        union { float f; uint32_t u; } t; t.f = v;
        hw[i] = (uint16_t) (t.u >> 16);
    }
    hipMemcpy(x, hx, N * 4, hipMemcpyHostToDevice);
    hipMemcpy(wa, hw, (size_t) N * 48 * 2, hipMemcpyHostToDevice);
    hipMemcpy(wb, hw, (size_t) N * 48 * 2, hipMemcpyHostToDevice);
    dim3 grid(12), block(256);
    // warmup
    for (int i = 0; i < 50; ++i) { ab_fmaf<<<grid, block>>>(x, wa, wb, o1, N); ab_dot2<<<grid, block>>>(x, wa, wb, o2, N); }
    hipDeviceSynchronize();
    const int reps = 2000;
    hipEvent_t t0, t1; hipEventCreate(&t0); hipEventCreate(&t1);
    float ms1, ms2;
    hipEventRecord(t0);
    for (int i = 0; i < reps; ++i) ab_fmaf<<<grid, block>>>(x, wa, wb, o1, N);
    hipEventRecord(t1); hipEventSynchronize(t1); hipEventElapsedTime(&ms1, t0, t1);
    hipEventRecord(t0);
    for (int i = 0; i < reps; ++i) ab_dot2<<<grid, block>>>(x, wa, wb, o2, N);
    hipEventRecord(t1); hipEventSynchronize(t1); hipEventElapsedTime(&ms2, t0, t1);
    // correctness: dot2 is expected to differ numerically (fp16 inputs); print both
    float* h1 = (float*) malloc(ROWS * 4); float* h2 = (float*) malloc(ROWS * 4);
    hipMemcpy(h1, o1, ROWS * 4, hipMemcpyDeviceToHost);
    hipMemcpy(h2, o2, ROWS * 4, hipMemcpyDeviceToHost);
    double n2 = 0, d2 = 0;
    for (int i = 0; i < ROWS; ++i) { n2 += (double) (h1[i] - h2[i]) * (h1[i] - h2[i]); d2 += (double) h1[i] * h1[i]; }
    double rel = d2 > 0 ? sqrt(n2 / d2) : 0;
    double us1 = ms1 * 1000.0 / reps, us2 = ms2 * 1000.0 / reps;
    double bytes = 2.0 * N * 48 * 2 + N * 4.0;   // wa+wb + x
    double gbs1 = bytes * reps / (ms1 * 1e-3) / 1e9, gbs2 = bytes * reps / (ms2 * 1e-3) / 1e9;
    std::printf("COLD(3 sets) ab_fmaf  T %d read %s us down %.1f\n", 1, "x", us1);
    std::printf("fmaf  %.2f us/call  %.1f GB/s\n", us1, gbs1);
    std::printf("dot2  %.2f us/call  %.1f GB/s  rel_rms %.6f\n", us2, gbs2, rel);
    std::printf("speedup %.3fx   (AI=%.2f MAC/B, gfx906 balance ~29)\n", us1 / us2, 2.0 * N * 48 / bytes);
    return 0;
}
