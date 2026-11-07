// W1046/R110: k8v4 PV dot8 feasibility prototype. Not part of the engine.
// V uses the production Q4_0 layout (18 B / 32 values); P*Vscale is quantized
// to signed INT4 per (head, 8 cells, 32-dimensional V block). v_dot8_i32_i4 is
// INT4 x INT4 on BOTH operands (ROCm/LLVM), never INT4 x INT8.
// P packing is PRECOMPUTED: timing
// is an upper bound. If this does not win, the full path cannot win.
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

constexpr int H = 12, C = 64, D = 256, B = 32, NB = D / B, GC = C / 8;
#pragma pack(push, 1)
struct BlockQ4 { uint16_t d; uint8_t qs[16]; };
#pragma pack(pop)
static_assert(sizeof(BlockQ4) == 18);

__device__ __forceinline__ int hw_dot8(int a, int b) {
#if defined(__HIP_DEVICE_COMPILE__) && defined(__gfx906__)
    return __builtin_amdgcn_sdot8(a, b, 0, false);
#else
    int r = 0;
    for (int i = 0; i < 8; ++i) {
        int a4 = (a >> (4 * i)) & 15; if (a4 >= 8) a4 -= 16;
        int b4 = (b >> (4 * i)) & 15; if (b4 >= 8) b4 -= 16;
        r += a4 * b4;
    }
    return r;
#endif
}
__device__ __forceinline__ float half_to_float(uint16_t h) {
    __half_raw r; r.x = h; return __half2float(*reinterpret_cast<__half*>(&r));
}
__host__ __device__ __forceinline__ int vcode(const BlockQ4* v, int c, int d) {
    const BlockQ4& b = v[c * NB + d / 32];
    int j = d & 31;
    int q = (b.qs[j & 15] >> (j < 16 ? 0 : 4)) & 15;
    return q - 8;
}

__global__ void pv_ref(const BlockQ4* v, const float* p, float* out) {
    int d = threadIdx.x, h = blockIdx.x;
    if (d >= D || h >= H) return;
    float acc = 0.f;
    for (int c = 0; c < C; ++c) {
        const BlockQ4& b = v[c * NB + d / 32];
        float vv = vcode(v, c, d) * half_to_float(b.d);
        acc = fmaf(p[h * C + c], vv, acc);
    }
    out[h * D + d] = acc;
}

__global__ void pv_dot8(const BlockQ4* v, const uint32_t* pq, const float* ps, float* out) {
    int d = threadIdx.x, h = blockIdx.x;
    if (d >= D || h >= H) return;
    float acc = 0.f;
    for (int g = 0; g < GC; ++g) {
        uint32_t vp = 0;
#pragma unroll
        for (int j = 0; j < 8; ++j) vp |= uint32_t(vcode(v, g * 8 + j, d) & 15) << (4 * j);
        int sum = hw_dot8(vp, pq[(h * GC + g) * NB + d / 32]);
        acc = fmaf((float) sum, ps[(h * GC + g) * NB + d / 32], acc);
    }
    out[h * D + d] = acc;
}

static double time_ms(void (*fn)(const BlockQ4*, const float*, float*), const BlockQ4* v,
                      const float* p, float* o, int reps) {
    hipEvent_t a, b; hipEventCreate(&a); hipEventCreate(&b);
    for (int i = 0; i < 20; ++i) fn<<<H, D>>>(v, p, o);
    hipEventRecord(a);
    for (int i = 0; i < reps; ++i) fn<<<H, D>>>(v, p, o);
    hipEventRecord(b); hipEventSynchronize(b);
    float ms = 0; hipEventElapsedTime(&ms, a, b); return ms / reps;
}
static double time_ms8(const BlockQ4* v, const uint32_t* q, const float* s, float* o, int reps) {
    hipEvent_t a, b; hipEventCreate(&a); hipEventCreate(&b);
    for (int i = 0; i < 20; ++i) pv_dot8<<<H, D>>>(v, q, s, o);
    hipEventRecord(a);
    for (int i = 0; i < reps; ++i) pv_dot8<<<H, D>>>(v, q, s, o);
    hipEventRecord(b); hipEventSynchronize(b);
    float ms = 0; hipEventElapsedTime(&ms, a, b); return ms / reps;
}

int main() {
    std::mt19937 rng(20261107);
    std::normal_distribution<float> nd(0.f, 1.f);
    std::vector<BlockQ4> hv(C * NB);
    std::vector<float> hp(H * C);
    for (int c = 0; c < C; ++c) for (int b = 0; b < NB; ++b) {
        float x[B]; float am = 0;
        for (float& z : x) { z = nd(rng); am = std::max(am, fabsf(z)); }
        float d = am > 0 ? am / 7.f : 1.f;
        __half hd = __float2half(d);
        hv[c * NB + b].d = *reinterpret_cast<uint16_t*>(&hd);
        for (int j = 0; j < 32; ++j) {
            int q = std::max(0, std::min(15, int(lroundf(x[j] / d)) + 8));
            hv[c * NB + b].qs[j & 15] |= uint8_t(q) << (j < 16 ? 0 : 4);
        }
    }
    for (int h = 0; h < H; ++h) {
        float m = -1e30f;
        for (int c = 0; c < C; ++c) { hp[h * C + c] = nd(rng) * 2.f; m = std::max(m, hp[h * C + c]); }
        float sum = 0;
        for (int c = 0; c < C; ++c) { hp[h * C + c] = expf(hp[h * C + c] - m); sum += hp[h * C + c]; }
        for (int c = 0; c < C; ++c) hp[h * C + c] /= sum;
    }
    std::vector<uint32_t> hpq(H * GC * NB, 0);
    std::vector<float> hps(H * GC * NB, 0);
    for (int h = 0; h < H; ++h) for (int g = 0; g < GC; ++g) for (int b = 0; b < NB; ++b) {
        float x[8], am = 0;
        for (int j = 0; j < 8; ++j) {
            float dv = __half2float(*reinterpret_cast<__half*>(&hv[(g * 8 + j) * NB + b].d));
            x[j] = hp[h * C + g * 8 + j] * dv; am = std::max(am, fabsf(x[j]));
        }
        float ds = am > 0 ? am / 7.f : 1.f;
        hps[(h * GC + g) * NB + b] = ds;
        for (int j = 0; j < 8; ++j) {
            int q = std::max(0, std::min(7, int(lroundf(x[j] / ds))));
            hpq[(h * GC + g) * NB + b] |= uint32_t(q) << (4 * j);
        }
    }
    BlockQ4* dv; float *dp, *dref, *dcand; uint32_t* dpq; float* dps;
    hipMalloc(&dv, hv.size() * sizeof(BlockQ4)); hipMalloc(&dp, hp.size() * 4);
    hipMalloc(&dref, H * D * 4); hipMalloc(&dcand, H * D * 4);
    hipMalloc(&dpq, hpq.size() * 4); hipMalloc(&dps, hps.size() * 4);
    hipMemcpy(dv, hv.data(), hv.size() * sizeof(BlockQ4), hipMemcpyHostToDevice);
    hipMemcpy(dp, hp.data(), hp.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(dpq, hpq.data(), hpq.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(dps, hps.data(), hps.size() * 4, hipMemcpyHostToDevice);
    pv_ref<<<H, D>>>(dv, dp, dref); pv_dot8<<<H, D>>>(dv, dpq, dps, dcand);
    std::vector<float> ref(H * D), cand(H * D);
    hipMemcpy(ref.data(), dref, ref.size() * 4, hipMemcpyDeviceToHost);
    hipMemcpy(cand.data(), dcand, cand.size() * 4, hipMemcpyDeviceToHost);
    double se = 0, sr = 0; float mx = 0;
    for (int i = 0; i < H * D; ++i) {
        double e = double(cand[i]) - ref[i]; se += e * e; sr += double(ref[i]) * ref[i];
        mx = std::max(mx, fabsf(cand[i] - ref[i]));
    }
    // CPU candidate with the identical packed math: separates quantisation design
    // errors from gfx906 operand-layout errors.
    for (int h = 0; h < 2; ++h) for (int d = 0; d < 4; ++d) {
        float acc = 0.f;
        for (int g = 0; g < GC; ++g) {
            int sum = 0;
            for (int j = 0; j < 8; ++j) {
                int vv = vcode(hv.data(), g * 8 + j, d);
                int qq = (hpq[(h * GC + g) * NB + d / 32] >> (4 * j)) & 15;
                sum += vv * qq;
            }
            acc += (float) sum * hps[(h * GC + g) * NB + d / 32];
        }
        int i = h * D + d;
        if (h == 0 && d == 0) {
            std::printf("HOST_DEBUG ds0=%.8g ps1=%.8g pq0=%08x p0=%.8g vscale0=%.8g\n",
                        hps[0], hps[1], hpq[0], hp[0],
                        __half2float(*reinterpret_cast<__half*>(&hv[0].d)));
        }
        std::printf("CPU_CHECK h=%d d=%d ref=%.8g gpu8=%.8g cpu8=%.8g\n", h, d, ref[i], cand[i], acc);
    }
    int reps = 2000;
    double tref = time_ms(pv_ref, dv, dp, dref, reps);
    double tdot = time_ms8(dv, dpq, dps, dcand, reps);
    std::printf("PV_DOT8_PROTO ref_us=%.3f dot8_prepacked_us=%.3f speedup=%.3fx rel_rms=%.6g max_abs=%.6g\n",
                tref * 1000, tdot * 1000, tref / tdot, sqrt(se / std::max(sr, 1e-30)), mx);
    std::printf("NOTE timing excludes P*Vscale quantization/packing; dot8 result is an upper bound, not an engine verdict.\n");
    return 0;
}
