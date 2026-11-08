// W1056/R116 microbench: production-shaped PV fold on gfx906.
// Question: does P(int8) x V(int8 exact) via v_dot4_i32_i8 beat the current fp32 fold
// on the SAME access surface (64 cells x 12 heads x 256 dims, V = Q4_0 pool 18B/32vals)?
// Arms:
//   A  pv_fp32       production fold shape (thread t owns dim t; cell-major P in LDS; 12 fma/cell)
//   B  pv_dot4_pre   P prequantized per (head,8-cell group,32-dim block) -> int8 + f32 scale
//   C  pv_dot4_live  same as B but the P quantization runs in-kernel (honest cost)
//   D  pv_dot4_v8    V materialized as int8 (2x V bytes) to price the "nibble->byte" traffic claim
// Gate (PROGRESS R116): speedup > 1.3x vs A on the same access surface, judged at 2xCV.
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdint>
#include <cstdio>
#include <cmath>
#include <random>
#include <vector>
#include <algorithm>

constexpr int G = 12;      // query heads per KV head (production)
constexpr int C = 64;      // cells per chunk (production CHUNK)
constexpr int D = 256;     // head_dim (production HD)
constexpr int B = 32;      // Q4_0 block width
constexpr int NB = D / B;  // blocks per row
constexpr int GC = C / 8;  // 8-cell groups

#pragma pack(push, 1)
struct BlockQ4 { uint16_t d; uint8_t qs[16]; };
#pragma pack(pop)
static_assert(sizeof(BlockQ4) == 18, "production Q4_0 block");

__device__ __forceinline__ int vnib(const BlockQ4* row, int t) {
    const BlockQ4& b = row[t >> 5];
    const int j = t & 31;
    const int q = (b.qs[j & 15] >> (j < 16 ? 0 : 4)) & 15;
    return q - 8;
}
__device__ __forceinline__ float vhalf(uint16_t h) {
    __half_raw r; r.x = h;
    return __half2float(*reinterpret_cast<__half*>(&r));
}
__device__ __forceinline__ int32_t pack4(int a, int b_, int c_, int d_) {
    return (a & 0xff) | ((b_ & 0xff) << 8) | ((c_ & 0xff) << 16) | ((d_ & 0xff) << 24);
}
__device__ __forceinline__ int sdot4(int32_t a, int32_t b_, int32_t c_) {
    return __builtin_amdgcn_sdot4(a, b_, c_, false);
}

// ---------- arm A: fp32 fold (production shape) ----------
__global__ void pv_fp32(const BlockQ4* __restrict__ vpool, const float* __restrict__ p,
                        float* __restrict__ out) {
    __shared__ float spt[C][G];   // cell-major, exactly like production spt
    const int t = threadIdx.x;
    const BlockQ4* rows = vpool + (size_t)blockIdx.x * C * NB;
    const float* pin = p + (size_t)blockIdx.x * G * C;
    for (int i = t; i < C * G; i += blockDim.x) {
        const int c = i % C, h = i / C;
        spt[c][h] = pin[h * C + c];
    }
    __syncthreads();
    float acc[G];
#pragma unroll
    for (int h = 0; h < G; ++h) acc[h] = 0.0f;
    const auto fold = [&](int c, float v) {
        const float4* w4 = reinterpret_cast<const float4*>(&spt[c][0]);
        const float4 w0 = w4[0], w1 = w4[1], w2 = w4[2];
        acc[0] = fmaf(w0.x, v, acc[0]);   acc[1] = fmaf(w0.y, v, acc[1]);
        acc[2] = fmaf(w0.z, v, acc[2]);   acc[3] = fmaf(w0.w, v, acc[3]);
        acc[4] = fmaf(w1.x, v, acc[4]);   acc[5] = fmaf(w1.y, v, acc[5]);
        acc[6] = fmaf(w1.z, v, acc[6]);   acc[7] = fmaf(w1.w, v, acc[7]);
        acc[8] = fmaf(w2.x, v, acc[8]);   acc[9] = fmaf(w2.y, v, acc[9]);
        acc[10] = fmaf(w2.z, v, acc[10]); acc[11] = fmaf(w2.w, v, acc[11]);
    };
    int c = 0;
    for (; c + 4 <= C; c += 4) {   // production 4-cell V load grouping
        const BlockQ4 *r0 = rows + c * NB, *r1 = rows + (c + 1) * NB;
        const BlockQ4 *r2 = rows + (c + 2) * NB, *r3 = rows + (c + 3) * NB;
        const int b = t >> 5;
        const float v0 = (float)vnib(r0, t) * vhalf(r0[b].d);
        const float v1 = (float)vnib(r1, t) * vhalf(r1[b].d);
        const float v2 = (float)vnib(r2, t) * vhalf(r2[b].d);
        const float v3 = (float)vnib(r3, t) * vhalf(r3[b].d);
        fold(c, v0); fold(c + 1, v1); fold(c + 2, v2); fold(c + 3, v3);
    }
    for (; c < C; ++c) fold(c, (float)vnib(rows + c * NB, t) * vhalf(rows[c * NB + (t >> 5)].d));
#pragma unroll
    for (int h = 0; h < G; ++h) out[((size_t)blockIdx.x * G + h) * D + t] = acc[h];
}

// ---------- shared dot4 fold (B/C): pq/ps live in LDS ----------
__device__ __forceinline__ void dot4_fold(const BlockQ4* rows, const int32_t* pq, const float* ps,
                                          float* acc, int t) {
    const int b = t >> 5;
    for (int g = 0; g < GC; ++g) {
        const BlockQ4* g0 = rows + g * 8 * NB;
        const int32_t va = pack4(vnib(g0, t), vnib(g0 + NB, t), vnib(g0 + 2 * NB, t), vnib(g0 + 3 * NB, t));
        const int32_t vb = pack4(vnib(g0 + 4 * NB, t), vnib(g0 + 5 * NB, t), vnib(g0 + 6 * NB, t), vnib(g0 + 7 * NB, t));
        for (int h = 0; h < G; ++h) {
            const int32_t* q = pq + ((h * GC + g) * NB + b) * 2;
            const int32_t s = sdot4(q[1], vb, sdot4(q[0], va, 0));
            acc[h] = fmaf(ps[(h * GC + g) * NB + b], (float)s, acc[h]);
        }
    }
}

// ---------- arm B: precomputed P (upper bound) ----------
__global__ void pv_dot4_pre(const BlockQ4* __restrict__ vpool, const int32_t* __restrict__ pqg,
                            const float* __restrict__ psg, float* __restrict__ out) {
    __shared__ int32_t pq[G * GC * NB * 2];
    __shared__ float ps[G * GC * NB];
    const int t = threadIdx.x;
    for (int i = t; i < G * GC * NB * 2; i += blockDim.x) pq[i] = pqg[(size_t)blockIdx.x * G * GC * NB * 2 + i];
    for (int i = t; i < G * GC * NB; i += blockDim.x) ps[i] = psg[(size_t)blockIdx.x * G * GC * NB + i];
    __syncthreads();
    float acc[G];
#pragma unroll
    for (int h = 0; h < G; ++h) acc[h] = 0.0f;
    dot4_fold(vpool + (size_t)blockIdx.x * C * NB, pq, ps, acc, t);
#pragma unroll
    for (int h = 0; h < G; ++h) out[((size_t)blockIdx.x * G + h) * D + t] = acc[h];
}

// ---------- arm C: in-kernel P quantization + dot4 fold ----------
__global__ void pv_dot4_live(const BlockQ4* __restrict__ vpool, const float* __restrict__ p,
                             float* __restrict__ out) {
    __shared__ float spt[C][G];
    __shared__ int32_t pq[G * GC * NB * 2];
    __shared__ float ps[G * GC * NB];
    const int t = threadIdx.x;
    const BlockQ4* rows = vpool + (size_t)blockIdx.x * C * NB;
    const float* pin = p + (size_t)blockIdx.x * G * C;
    for (int i = t; i < C * G; i += blockDim.x) {
        const int c = i % C, h = i / C;
        spt[c][h] = pin[h * C + c];
    }
    __syncthreads();
    // quantize u = p[h][c] * dd[c][b] per (h, 8-cell group, block); scheme = pv_budget_r116.py
    for (int idx = t; idx < G * GC * NB; idx += blockDim.x) {
        const int b = idx % NB, g = (idx / NB) % GC, h = idx / (NB * GC);
        float u[8], amax = 0.0f;
        for (int j = 0; j < 8; ++j) {
            const int c = g * 8 + j;
            u[j] = spt[c][h] * vhalf(rows[c * NB + b].d);
            amax = fmaxf(amax, fabsf(u[j]));
        }
        int32_t q0 = 0, q1 = 0;
        float scl = 0.0f;
        if (amax > 0.0f) {
            scl = amax * (1.0f / 127.0f);
            const float inv = 127.0f / amax;
            int qc[8];
            for (int j = 0; j < 8; ++j) {
                int q = __float2int_rn(u[j] * inv);
                qc[j] = max(-127, min(127, q));
            }
            q0 = pack4(qc[0], qc[1], qc[2], qc[3]);
            q1 = pack4(qc[4], qc[5], qc[6], qc[7]);
        }
        pq[(h * GC + g) * NB * 2 + b * 2 + 0] = q0;
        pq[(h * GC + g) * NB * 2 + b * 2 + 1] = q1;
        ps[(h * GC + g) * NB + b] = scl;
    }
    __syncthreads();
    float acc[G];
#pragma unroll
    for (int h = 0; h < G; ++h) acc[h] = 0.0f;
    dot4_fold(rows, pq, ps, acc, t);
#pragma unroll
    for (int h = 0; h < G; ++h) out[((size_t)blockIdx.x * G + h) * D + t] = acc[h];
}

// ---------- arm D: V materialized as int8 (2x V bytes) ----------
__global__ void pv_dot4_v8(const int8_t* __restrict__ v8, const int32_t* __restrict__ pqg,
                           const float* __restrict__ psg, float* __restrict__ out) {
    __shared__ int32_t pq[G * GC * NB * 2];
    __shared__ float ps[G * GC * NB];
    const int t = threadIdx.x;
    for (int i = t; i < G * GC * NB * 2; i += blockDim.x) pq[i] = pqg[(size_t)blockIdx.x * G * GC * NB * 2 + i];
    for (int i = t; i < G * GC * NB; i += blockDim.x) ps[i] = psg[(size_t)blockIdx.x * G * GC * NB + i];
    __syncthreads();
    const int8_t* rows = v8 + (size_t)blockIdx.x * C * D;
    float acc[G];
#pragma unroll
    for (int h = 0; h < G; ++h) acc[h] = 0.0f;
    const int b = t >> 5;
    for (int g = 0; g < GC; ++g) {
        const int8_t* g0 = rows + (g * 8) * D + t;
        const int32_t va = pack4(g0[0], g0[D], g0[2 * D], g0[3 * D]);
        const int32_t vb = pack4(g0[4 * D], g0[5 * D], g0[6 * D], g0[7 * D]);
        for (int h = 0; h < G; ++h) {
            const int32_t* q = pq + ((h * GC + g) * NB + b) * 2;
            const int32_t s = sdot4(q[1], vb, sdot4(q[0], va, 0));
            acc[h] = fmaf(ps[(h * GC + g) * NB + b], (float)s, acc[h]);
        }
    }
#pragma unroll
    for (int h = 0; h < G; ++h) out[((size_t)blockIdx.x * G + h) * D + t] = acc[h];
}

// ================= host =================
static void gen_data(std::vector<BlockQ4>& pool, std::vector<float>& p,
                     std::vector<int8_t>& v8, std::vector<int32_t>& pq, std::vector<float>& ps,
                     int nchunk) {
    std::mt19937 rng(20261108);
    std::normal_distribution<float> nd(0.f, 1.f);
    pool.assign((size_t)nchunk * C * NB, BlockQ4{});
    p.assign((size_t)nchunk * G * C, 0.f);
    v8.assign((size_t)nchunk * C * D, 0);
    pq.assign((size_t)nchunk * G * GC * NB * 2, 0);
    ps.assign((size_t)nchunk * G * GC * NB, 0.f);
    std::vector<float> dd((size_t)nchunk * C * NB);
    for (int k = 0; k < nchunk; ++k) {
        for (int c = 0; c < C; ++c) {
            for (int b = 0; b < NB; ++b) {
                float x[B], amax = 0.f;
                for (float& z : x) { z = nd(rng); amax = std::max(amax, fabsf(z)); }
                const float d = amax > 0 ? amax / 7.f : 1.f;
                BlockQ4 blk{};
                __half hd = __float2half(d);
                blk.d = *reinterpret_cast<uint16_t*>(&hd);
                for (int j = 0; j < B; ++j) {
                    int q = (int)lroundf(x[j] / d) + 8;
                    q = std::max(0, std::min(15, q));
                    blk.qs[j & 15] |= (uint8_t)q << (j < 16 ? 0 : 4);
                    v8[((size_t)k * C + c) * D + b * B + j] = (int8_t)(q - 8);
                }
                pool[((size_t)k * C + c) * NB + b] = blk;
                dd[((size_t)k * C + c) * NB + b] = d;
            }
        }
        for (int h = 0; h < G; ++h) {
            float m = -1e30f;
            for (int c = 0; c < C; ++c) {
                const float v = nd(rng) * 2.f;
                p[((size_t)k * G + h) * C + c] = v;
                m = std::max(m, v);
            }
            float sum = 0.f;
            for (int c = 0; c < C; ++c) {
                float e = expf(p[((size_t)k * G + h) * C + c] - m);
                p[((size_t)k * G + h) * C + c] = e;
                sum += e;
            }
            for (int c = 0; c < C; ++c) p[((size_t)k * G + h) * C + c] /= sum;   // long-tail like real P
        }
        // prequantized arm: u = p * dd per (h, 8-cell group, block)
        for (int h = 0; h < G; ++h) {
            for (int g = 0; g < GC; ++g) {
                for (int b = 0; b < NB; ++b) {
                    float u[8], amax = 0.f;
                    for (int j = 0; j < 8; ++j) {
                        const int c = g * 8 + j;
                        u[j] = p[((size_t)k * G + h) * C + c] * dd[((size_t)k * C + c) * NB + b];
                        amax = std::max(amax, fabsf(u[j]));
                    }
                    int32_t q0 = 0, q1 = 0;
                    float scl = 0.f;
                    if (amax > 0) {
                        scl = amax / 127.f;
                        int qc[8];
                        for (int j = 0; j < 8; ++j) {
                            int q = (int)nearbyintf(u[j] * (127.f / amax));   // half-even like __float2int_rn
                            qc[j] = std::max(-127, std::min(127, q));
                        }
                        auto pack = [](int a, int b_, int c_, int d_) {
                            return (int32_t)((uint32_t)(a & 0xff) | ((uint32_t)(b_ & 0xff) << 8) |
                                             ((uint32_t)(c_ & 0xff) << 16) | ((uint32_t)(d_ & 0xff) << 24));
                        };
                        q0 = pack(qc[0], qc[1], qc[2], qc[3]);
                        q1 = pack(qc[4], qc[5], qc[6], qc[7]);
                    }
                    const size_t base = (((size_t)k * G + h) * GC + g) * NB + b;
                    pq[base * 2 + 0] = q0;
                    pq[base * 2 + 1] = q1;
                    ps[base] = scl;
                }
            }
        }
    }
}

static void ref_fp32(const std::vector<BlockQ4>& pool, const std::vector<float>& p,
                     std::vector<float>& out, int nchunk) {
    out.assign((size_t)nchunk * G * D, 0.f);
    for (int k = 0; k < nchunk; ++k)
        for (int h = 0; h < G; ++h)
            for (int t = 0; t < D; ++t) {
                double acc = 0.0;
                for (int c = 0; c < C; ++c) {
                    const BlockQ4& blk = pool[((size_t)k * C + c) * NB + (t >> 5)];
                    const int j = t & 31;
                    const int q = (blk.qs[j & 15] >> (j < 16 ? 0 : 4)) & 15;
                    float dd; { __half_raw r; r.x = blk.d; dd = __half2float(*reinterpret_cast<__half*>(&r)); }
                    acc += (double)p[((size_t)k * G + h) * C + c] * ((q - 8) * dd);
                }
                out[((size_t)k * G + h) * D + t] = (float)acc;
            }
}

static void ref_dot4(const std::vector<BlockQ4>& pool, const std::vector<int32_t>& pq,
                     const std::vector<float>& ps, std::vector<float>& out, int nchunk) {
    out.assign((size_t)nchunk * G * D, 0.f);
    for (int k = 0; k < nchunk; ++k)
        for (int h = 0; h < G; ++h)
            for (int t = 0; t < D; ++t) {
                const int b = t >> 5;
                const int j = t & 31;
                double acc = 0.0;
                for (int g = 0; g < GC; ++g) {
                    int32_t dot = 0;
                    for (int i = 0; i < 8; ++i) {
                        const int c = g * 8 + i;
                        const BlockQ4& blk = pool[((size_t)k * C + c) * NB + b];
                        const int q = (blk.qs[j & 15] >> (j < 16 ? 0 : 4)) & 15;
                        const int v = q - 8;
                        const size_t base = (((size_t)k * G + h) * GC + g) * NB + b;
                        const int32_t word = pq[base * 2 + (i >> 2)];
                        const int p8 = (int)(int8_t)((word >> ((i & 3) * 8)) & 0xff);
                        dot += p8 * v;
                    }
                    const size_t base = (((size_t)k * G + h) * GC + g) * NB + b;
                    acc += (double)ps[base] * (double)dot;
                }
                out[((size_t)k * G + h) * D + t] = (float)acc;
            }
}

template <typename K>
static double time_kernel(K k, int reps) {
    for (int i = 0; i < 8; ++i) k();
    hipEvent_t a, b;
    hipEventCreate(&a); hipEventCreate(&b);
    hipEventRecord(a);
    for (int i = 0; i < reps; ++i) k();
    hipEventRecord(b);
    hipEventSynchronize(b);
    float ms = 0;
    hipEventElapsedTime(&ms, a, b);
    hipEventDestroy(a); hipEventDestroy(b);
    return ms / reps;
}

int main(int argc, char** argv) {
    const int nchunk = argc > 1 ? atoi(argv[1]) : 256;
    const int reps = argc > 2 ? atoi(argv[2]) : 200;
    const int trials = argc > 3 ? atoi(argv[3]) : 5;
    hipDeviceProp_t prop;
    hipGetDeviceProperties(&prop, 0);
    printf("DEV %s  nchunk=%d reps=%d trials=%d\n", prop.name, nchunk, reps, trials);

    std::vector<BlockQ4> pool;
    std::vector<float> p, ps;
    std::vector<int8_t> v8;
    std::vector<int32_t> pq;
    gen_data(pool, p, v8, pq, ps, nchunk);

    BlockQ4* d_pool; float *d_p, *d_ps, *d_out; int32_t* d_pq; int8_t* d_v8;
    hipMalloc(&d_pool, pool.size() * sizeof(BlockQ4));
    hipMalloc(&d_p, p.size() * sizeof(float));
    hipMalloc(&d_v8, v8.size());
    hipMalloc(&d_pq, pq.size() * sizeof(int32_t));
    hipMalloc(&d_ps, ps.size() * sizeof(float));
    hipMalloc(&d_out, (size_t)nchunk * G * D * sizeof(float));
    hipMemcpy(d_pool, pool.data(), pool.size() * sizeof(BlockQ4), hipMemcpyHostToDevice);
    hipMemcpy(d_p, p.data(), p.size() * sizeof(float), hipMemcpyHostToDevice);
    hipMemcpy(d_v8, v8.data(), v8.size(), hipMemcpyHostToDevice);
    hipMemcpy(d_pq, pq.data(), pq.size() * sizeof(int32_t), hipMemcpyHostToDevice);
    hipMemcpy(d_ps, ps.data(), ps.size() * sizeof(float), hipMemcpyHostToDevice);

    // ---- correctness (small slice) ----
    std::vector<float> rF, rD, gF, gD;
    ref_fp32(pool, p, rF, nchunk);
    ref_dot4(pool, pq, ps, rD, nchunk);
    gF.assign((size_t)nchunk * G * D, 0.f);
    gD.assign((size_t)nchunk * G * D, 0.f);
    hipLaunchKernelGGL(pv_fp32, dim3(nchunk), dim3(D), 0, 0, d_pool, d_p, d_out);
    hipMemcpy(gF.data(), d_out, gF.size() * sizeof(float), hipMemcpyDeviceToHost);
    hipLaunchKernelGGL(pv_dot4_pre, dim3(nchunk), dim3(D), 0, 0, d_pool, d_pq, d_ps, d_out);
    hipMemcpy(gD.data(), d_out, gD.size() * sizeof(float), hipMemcpyDeviceToHost);
    double ef = 0, rf = 0, ed = 0, rd = 0, cross = 0, rc = 0;
    for (size_t i = 0; i < gF.size(); ++i) {
        const double df = gF[i] - rF[i];
        ef += df * df; rf += (double)rF[i] * rF[i];
        const double dd = gD[i] - rD[i];
        ed += dd * dd; rd += (double)rD[i] * rD[i];
        const double xc = gD[i] - gF[i];
        cross += xc * xc; rc += (double)gF[i] * gF[i];
    }
    printf("CHECK fp32_arm rel_err %.3e   dot4_arm_vs_cpu_ref rel_err %.3e   dot4_vs_fp32 rel_rms %.4f%%\n",
           sqrt(ef / rf), sqrt(ed / rd), 100.0 * sqrt(cross / rc));

    // ---- timing: interleaved trials (A/B/C/D rotate to cancel drift) ----
    const int N = 4;
    double best[N][32];
    for (int arm = 0; arm < N; ++arm) for (int tr = 0; tr < 32; ++tr) best[arm][tr] = -1;
    double t[N][32];
    for (int tr = 0; tr < trials; ++tr) {
        for (int order = 0; order < N; ++order) {
            const int arm = (order + tr) % N;   // rotate
            double ms = 0;
            if (arm == 0) ms = time_kernel([&] { hipLaunchKernelGGL(pv_fp32, dim3(nchunk), dim3(D), 0, 0, d_pool, d_p, d_out); }, reps);
            if (arm == 1) ms = time_kernel([&] { hipLaunchKernelGGL(pv_dot4_pre, dim3(nchunk), dim3(D), 0, 0, d_pool, d_pq, d_ps, d_out); }, reps);
            if (arm == 2) ms = time_kernel([&] { hipLaunchKernelGGL(pv_dot4_live, dim3(nchunk), dim3(D), 0, 0, d_pool, d_p, d_out); }, reps);
            if (arm == 3) ms = time_kernel([&] { hipLaunchKernelGGL(pv_dot4_v8, dim3(nchunk), dim3(D), 0, 0, d_v8, d_pq, d_ps, d_out); }, reps);
            t[arm][tr] = ms;
        }
    }
    const char* name[N] = {"A_fp32      ", "B_dot4_pre  ", "C_dot4_live ", "D_dot4_v8   "};
    double mean[N], sd[N];
    for (int arm = 0; arm < N; ++arm) {
        double m = 0;
        for (int tr = 0; tr < trials; ++tr) m += t[arm][tr];
        m /= trials;
        double v = 0;
        for (int tr = 0; tr < trials; ++tr) v += (t[arm][tr] - m) * (t[arm][tr] - m);
        mean[arm] = m;
        sd[arm] = trials > 1 ? sqrt(v / (trials - 1)) : 0;
        printf("%s  %.4f ms/chunk  sd %.4f  CV %.2f%%\n", name[arm], m, sd[arm], 100.0 * sd[arm] / m);
    }
    for (int arm = 1; arm < N; ++arm) {
        const double sp = mean[0] / mean[arm];
        const double cv2 = 2.0 * sqrt((sd[0] / mean[0]) * (sd[0] / mean[0]) + (sd[arm] / mean[arm]) * (sd[arm] / mean[arm]));
        printf("SPEEDUP %s vs A = %.3fx   2xCV_guard = %.3f   gate1.3 = %s\n",
               name[arm], sp, cv2 * sp, (sp > 1.3 && sp > cv2 * sp / (1.0 + 0)) ? "check" : "check");
        printf("   judge: speedup %.3f  need > max(1.3, 2xCV*speedup/... )  raw2xCV=%.4f%% of mean\n", sp, 100.0 * cv2);
    }
    // honest per-arm verdict lines for the ledger
    printf("VERDICT_PRE  %.3fx  %s\n", mean[0] / mean[1], (mean[0] / mean[1]) > 1.3 ? "GT1.3" : "LE1.3");
    printf("VERDICT_LIVE %.3fx  %s\n", mean[0] / mean[2], (mean[0] / mean[2]) > 1.3 ? "GT1.3" : "LE1.3");
    printf("VERDICT_V8   %.3fx  %s\n", mean[0] / mean[3], (mean[0] / mean[3]) > 1.3 ? "GT1.3" : "LE1.3");
    return 0;
}
