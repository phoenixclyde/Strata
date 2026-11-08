// W1058 / R91 P1+P3 harness + same-access microbench  (gfx906, HIP)
//
// P1  gate: BlockA4 quantizer (scale=amax/7, roundf, clamp [-8,7], bare int16 sa in header)
//            GPU kernel vs CPU reference -> element-wise BIT-EXACT (codes, d bits, sa)
//            formula pinned to a4sim/R74 (deploy P583): d_inv=7/amax, q=roundf(x*d_inv), clamp
// P3  gate: vec_dot_q4_K_q4_impl_mmq  = sdot8(q^0x88888888, a) + 8*Sigma_a , min term * Sigma_a
//            vs dp4a arm on identical int4 codes -> integer sums BIT-EXACT
//            vs fp64 dequant reference -> rel_l2 (fp32 scaling rounding only)
// ubench: arm A dp4a W4A8 (production inner loop) / arm B sdot8 + in-loop repack (no P2)
//            / arm C sdot8 pre-packed nibbles (P2 ideal, half activation bytes)
//            weight row LDS-cached (fixes w947's 8x weight traffic flaw), interleaved trials
//
// Build flags copied verbatim from build-masterp build.ninja mmq-instance-q4_k rule:
//   -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <random>
#include <algorithm>

#define QK_K 256
#define K_DIM 2560
#define N_ROWS 1280
#define M_TOK  64
#define TPW    8

struct BlockQ4K {
    _Float16 d;
    _Float16 dmin;
    unsigned char scales[12];
    unsigned char qs[128];
};

// ---- P1 block format (W951 P1: "float -> int4 (每 32 值一组 scale + Σa，写进 block 头)")
// sa is the BARE integer sum of the 32 int4 codes (needed in int32 domain by the
// sdot8 recenter +8*sa).  Deliberate difference vs Q8_1 header (which stores d*sum_q
// as fp16) — documented in the W1058 report.
struct BlockA4 {
    _Float16 d;        // scale = amax/7 (fp32 math, stored fp16 like Q8_1)
    int16_t  sa;       // sum of 32 codes, codes in [-8,7] -> sa in [-256,224]
    unsigned char qs[16]; // 32 codes, two's-complement nibbles; value k in nibble k
};

static __host__ __device__ inline void get_scale_min_k4(int j, const unsigned char * q,
                                                        unsigned char * d, unsigned char * m) {
    if (j < 4) { *d = q[j] & 63; *m = q[j + 4] & 63; }
    else { *d = (q[j+4] & 0x0F) | ((q[j-4] >> 6) << 4); *m = (q[j+4] >> 4) | ((q[j] >> 6) << 4); }
}

static __host__ __device__ inline unsigned pack8_u4(const unsigned char * qs16, int g) {
    unsigned r = 0;
#pragma unroll
    for (int i = 0; i < 8; i++) {
        const int idx = g * 8 + i;
        const unsigned v = (idx < 16) ? (qs16[idx] & 0xF) : (qs16[idx - 16] >> 4);
        r |= (v & 0xF) << (4 * i);
    }
    return r;
}

__device__ __forceinline__ int sdot4(int a, int b, int c) { return __builtin_amdgcn_sdot4(a, b, c, false); }
__device__ __forceinline__ int sdot8(int a, int b, int c) { return __builtin_amdgcn_sdot8(a, b, c, false); }

// ---------------- P1 : quantizer ----------------
// CPU reference — same expressions as a4sim_patch.py (W1057/R74, P583):
//   d_inv = amax>0 ? 7/amax : 0 ; d = amax>0 ? amax/7 : 0
//   q = roundf(x*d_inv) ; clamp to [-8,7]
static void quant_a4_cpu(const float * x, BlockA4 * out, int nblk) {
    for (int b = 0; b < nblk; b++) {
        const float * p = x + (size_t) b * 32;
        float amax = 0.0f;
        for (int i = 0; i < 32; i++) amax = fmaxf(amax, fabsf(p[i]));
        const float d_inv = amax > 0.0f ? 7.0f / amax : 0.0f;
        const float d     = amax > 0.0f ? amax / 7.0f : 0.0f;
        int16_t sa = 0;
        unsigned char qs[16]; memset(qs, 0, 16);
        for (int i = 0; i < 32; i++) {
            float qf = roundf(p[i] * d_inv);
            int q = (int) qf;
            if (q > 7) q = 7;
            if (q < -8) q = -8;
            sa += (int16_t) q;
            const int nib = q & 0xF;
            if ((i & 1) == 0) qs[i/2] |= (unsigned char) nib;
            else              qs[i/2] |= (unsigned char) (nib << 4);
        }
        out[b].d  = (_Float16) d;
        out[b].sa = sa;
        memcpy(out[b].qs, qs, 16);
    }
}

__global__ void quant_a4_gpu(const float * __restrict__ x, BlockA4 * __restrict__ out, int nblk) {
    const int b = blockIdx.x * blockDim.x + threadIdx.x;
    if (b >= nblk) return;
    const float * p = x + (size_t) b * 32;
    float amax = 0.0f;
    for (int i = 0; i < 32; i++) amax = fmaxf(amax, fabsf(p[i]));
    const float d_inv = amax > 0.0f ? 7.0f / amax : 0.0f;
    const float d     = amax > 0.0f ? amax / 7.0f : 0.0f;
    int16_t sa = 0;
    unsigned char qs[16]; memset(qs, 0, 16);
    for (int i = 0; i < 32; i++) {
        float qf = roundf(p[i] * d_inv);
        int q = (int) qf;
        if (q > 7) q = 7;
        if (q < -8) q = -8;
        sa += (int16_t) q;
        const int nib = q & 0xF;
        if ((i & 1) == 0) qs[i/2] |= (unsigned char) nib;
        else              qs[i/2] |= (unsigned char) (nib << 4);
    }
    out[b].d  = (_Float16) d;
    out[b].sa = sa;
#pragma unroll
    for (int i = 0; i < 16; i++) out[b].qs[i] = qs[i];
}

// ---------------- P3 : vec_dot ----------------
// sdot8 recenter, per 8 values (W927/W947 formula, verbatim math):
//   qx = q8 ^ 0x88888888          -> (q-8) as signed nibbles
//   sd = sdot8(qx, xs, 0)         -> sum (q-8)*a
//   sumi = sd + 8*sa8             -> sum q*a
__device__ __forceinline__ int dot8_recenter(unsigned q8, int xs_packed, int sa8) {
    const int qx = (int) (q8 ^ 0x88888888u);
    const int sd = sdot8(qx, xs_packed, 0);
    return sd + 8 * sa8;
}

// pack 8 signed codes (bytes, values in [-8,7]) into 8 signed nibbles in one int32
__device__ __forceinline__ int pack8_i4_from_bytes(const signed char * p) {
    int r = 0;
#pragma unroll
    for (int i = 0; i < 8; i++) r |= ((int) (p[i] & 0xF)) << (4 * i);
    return r;
}
__device__ __forceinline__ int sum8_bytes(const signed char * p) {
    int s = 0;
#pragma unroll
    for (int i = 0; i < 8; i++) s += (int) p[i];
    return s;
}
__device__ __forceinline__ int sum8_nib(int packed) {
    int s = 0;
#pragma unroll
    for (int i = 0; i < 8; i++) {
        int v = (packed >> (4 * i)) & 0xF;
        if (v & 0x8) v -= 16;
        s += v;
    }
    return s;
}

// ---------------- GEMM kernels (production gate/up shape M=64 x N=1280 x K=2560) ----------------
// weight row cached in LDS once per block (fixes w947's 8x traffic flaw);
// activation rows read from global (arm A/B: 1 B/code; arm C: packed 0.5 B/code);
// REPS in-kernel repetitions -> inner-loop cost dominates.

__global__ void gemm_A_dp4a(const BlockQ4K * __restrict__ w, const signed char * __restrict__ xq8,
                            const int * __restrict__ sx8, const float * __restrict__ s8,
                            float * __restrict__ y, int k, int reps) {
    const int row = blockIdx.x, lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    const int t0 = warp * TPW;
    const int nblk = k / QK_K;
    extern __shared__ unsigned char smem[];
    BlockQ4K * wrow = (BlockQ4K *) smem;
    if (threadIdx.x < nblk) wrow[threadIdx.x] = w[(size_t) row * nblk + threadIdx.x];
    for (int t = threadIdx.x; t < nblk; t += blockDim.x) wrow[t] = w[(size_t) row * nblk + t];
    __syncthreads();
    float acc[TPW];
#pragma unroll
    for (int i = 0; i < TPW; i++) acc[i] = 0.0f;
    for (int rep = 0; rep < reps; rep++) {
        for (int base = lane * 8; base < k; base += 32 * 8) {
            const BlockQ4K * b = wrow + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m;
            get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned q8 = pack8_u4(b->qs + 16 * j, g);
            int vi0 = 0, vi1 = 0;
#pragma unroll
            for (int i = 0; i < 4; i++) {
                vi0 |= (int) ((q8 >> (4 * i)) & 0xF) << (8 * i);
                vi1 |= (int) ((q8 >> (4 * (i + 4))) & 0xF) << (8 * i);
            }
            const float dm_d = (float) b->d * (float) sc, dm_m = (float) b->dmin * (float) m;
#pragma unroll
            for (int t = 0; t < TPW; t++) {
                const int tok = t0 + t;
                const signed char * xr = xq8 + (size_t) tok * k + base;
                int xi0 = 0, xi1 = 0;
#pragma unroll
                for (int i = 0; i < 4; i++) {
                    xi0 |= (int) ((unsigned char) xr[i]) << (8 * i);
                    xi1 |= (int) ((unsigned char) xr[i + 4]) << (8 * i);
                }
                int sumi = sdot4(vi0, xi0, 0);
                sumi = sdot4(vi1, xi1, sumi);
                const float s = s8[(size_t) tok * (k / 32) + base / 32];
                const int sx = sx8[(size_t) tok * (k / 8) + base / 8];
                acc[t] += dm_d * (s * (float) sumi) - dm_m * (s * (float) sx);
            }
        }
    }
    const int lane_ = threadIdx.x & 31;
#pragma unroll
    for (int t = 0; t < TPW; t++) {
        float v = acc[t];
#pragma unroll
        for (int o = 16; o > 0; o >>= 1) v += __shfl_down_sync(0xffffffffffffffffull, v, o);
        if (lane_ == 0) y[(size_t) (t0 + t) * N_ROWS + row] = v;
    }
}

// arm B: sdot8 with in-loop repack from the int8 container (no P2)
__global__ void gemm_B_repack(const BlockQ4K * __restrict__ w, const signed char * __restrict__ xq8,
                              const float * __restrict__ s8,
                              float * __restrict__ y, int k, int reps) {
    const int row = blockIdx.x, lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    const int t0 = warp * TPW;
    const int nblk = k / QK_K;
    extern __shared__ unsigned char smem[];
    BlockQ4K * wrow = (BlockQ4K *) smem;
    for (int t = threadIdx.x; t < nblk; t += blockDim.x) wrow[t] = w[(size_t) row * nblk + t];
    __syncthreads();
    float acc[TPW];
#pragma unroll
    for (int i = 0; i < TPW; i++) acc[i] = 0.0f;
    for (int rep = 0; rep < reps; rep++) {
        for (int base = lane * 8; base < k; base += 32 * 8) {
            const BlockQ4K * b = wrow + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m;
            get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned q8 = pack8_u4(b->qs + 16 * j, g);
            const float dm_d = (float) b->d * (float) sc, dm_m = (float) b->dmin * (float) m;
#pragma unroll
            for (int t = 0; t < TPW; t++) {
                const int tok = t0 + t;
                const signed char * xr = xq8 + (size_t) tok * k + base;
                const int xs = pack8_i4_from_bytes(xr);
                const int sa8 = sum8_bytes(xr);
                const int sumi = dot8_recenter(q8, xs, sa8);
                const float s = s8[(size_t) tok * (k / 32) + base / 32];
                acc[t] += dm_d * (s * (float) sumi) - dm_m * (s * (float) sa8);
            }
        }
    }
    const int lane_ = threadIdx.x & 31;
#pragma unroll
    for (int t = 0; t < TPW; t++) {
        float v = acc[t];
#pragma unroll
        for (int o = 16; o > 0; o >>= 1) v += __shfl_down_sync(0xffffffffffffffffull, v, o);
        if (lane_ == 0) y[(size_t) (t0 + t) * N_ROWS + row] = v;
    }
}

// arm C: sdot8 on pre-packed nibbles (P2 ideal: activation stream halves)
__global__ void gemm_C_packed(const BlockQ4K * __restrict__ w, const int * __restrict__ xq4,
                              const int * __restrict__ sa4, const float * __restrict__ s8,
                              float * __restrict__ y, int k, int reps) {
    const int row = blockIdx.x, lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    const int t0 = warp * TPW;
    const int nblk = k / QK_K;
    extern __shared__ unsigned char smem[];
    BlockQ4K * wrow = (BlockQ4K *) smem;
    for (int t = threadIdx.x; t < nblk; t += blockDim.x) wrow[t] = w[(size_t) row * nblk + t];
    __syncthreads();
    float acc[TPW];
#pragma unroll
    for (int i = 0; i < TPW; i++) acc[i] = 0.0f;
    for (int rep = 0; rep < reps; rep++) {
        for (int base = lane * 8; base < k; base += 32 * 8) {
            const BlockQ4K * b = wrow + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m;
            get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned q8 = pack8_u4(b->qs + 16 * j, g);
            const float dm_d = (float) b->d * (float) sc, dm_m = (float) b->dmin * (float) m;
#pragma unroll
            for (int t = 0; t < TPW; t++) {
                const int tok = t0 + t;
                const int xs = xq4[(size_t) tok * (k / 8) + base / 8];
                const int sa8 = sa4[(size_t) tok * (k / 8) + base / 8];
                const int sumi = dot8_recenter(q8, xs, sa8);
                const float s = s8[(size_t) tok * (k / 32) + base / 32];
                acc[t] += dm_d * (s * (float) sumi) - dm_m * (s * (float) sa8);
            }
        }
    }
    const int lane_ = threadIdx.x & 31;
#pragma unroll
    for (int t = 0; t < TPW; t++) {
        float v = acc[t];
#pragma unroll
        for (int o = 16; o > 0; o >>= 1) v += __shfl_down_sync(0xffffffffffffffffull, v, o);
        if (lane_ == 0) y[(size_t) (t0 + t) * N_ROWS + row] = v;
    }
}

// ---------------- host helpers ----------------
static double ref_rel_l2(const std::vector<float> & y, const std::vector<double> & ref,
                         int rows, int tokens) {
    double n = 0, d = 0;
    for (int t = 0; t < tokens; t++) for (int o = 0; o < rows; o++) {
        const double a = y[(size_t) t * rows + o], b = ref[(size_t) t * rows + o];
        n += (a - b) * (a - b); d += b * b;
    }
    return d > 0 ? sqrt(n / d) : 0.0;
}

int main(int argc, char ** argv) {
    hipDeviceProp_t prop; hipGetDeviceProperties(&prop, 0);
    const int reps   = argc > 1 ? atoi(argv[1]) : 8;
    const int trials = argc > 2 ? atoi(argv[2]) : 5;
    printf("DEV %s  K=%d N=%d M=%d reps=%d trials=%d\n", prop.name, K_DIM, N_ROWS, M_TOK, reps, trials);

    std::mt19937 rng(1058);

    // ================= P1 gate =================
    {
        const int nblk = 4096;
        std::vector<float> x((size_t) nblk * 32);
        for (auto & v : x) v = (float) ((int) (rng() % 2001) - 1000) / 500.0f;
        // deliberate edge blocks: zeros / exact-tie / saturation
        for (int i = 0; i < 32; i++) x[i] = 0.0f;
        for (int i = 0; i < 32; i++) x[32 + i] = 0.5f * 7.0f / 7.0f * ((i & 1) ? 1.0f : -1.0f); // ties at 0.5
        for (int i = 0; i < 32; i++) x[64 + i] = (i == 31) ? 7.0f : 1e-6f; // amax at one lane
        for (int i = 0; i < 32; i++) x[96 + i] = -8.5f; // clamp low side
        std::vector<BlockA4> ref(nblk), got(nblk);
        quant_a4_cpu(x.data(), ref.data(), nblk);
        float * dx; BlockA4 * db;
        hipMalloc(&dx, x.size() * 4); hipMalloc(&db, nblk * sizeof(BlockA4));
        hipMemcpy(dx, x.data(), x.size() * 4, hipMemcpyHostToDevice);
        quant_a4_gpu<<<(nblk + 255) / 256, 256>>>(dx, db, nblk);
        hipDeviceSynchronize();
        hipMemcpy(got.data(), db, nblk * sizeof(BlockA4), hipMemcpyDeviceToHost);
        int bad = 0, bad_sa = 0, bad_d = 0, bad_qs = 0;
        for (int b = 0; b < nblk; b++) {
            if (got[b].sa != ref[b].sa) { bad_sa++; bad++; }
            if (memcmp(&got[b].d, &ref[b].d, 2) != 0) { bad_d++; bad++; }
            if (memcmp(got[b].qs, ref[b].qs, 16) != 0) { bad_qs++; bad++; }
        }
        printf("P1 gate: blocks=%d  mismatch=%d (sa=%d d=%d qs=%d) -> %s\n",
               nblk, bad, bad_sa, bad_d, bad_qs, bad == 0 ? "PASS" : "FAIL");
        if (bad != 0) { printf("P1 FAIL\n"); return 2; }
    }

    // ================= P3 correctness =================
    const int nblk = K_DIM / QK_K;
    std::vector<BlockQ4K> w((size_t) N_ROWS * nblk);
    for (auto & b : w) {
        b.d = (_Float16) (0.01f + (rng() % 100) * 0.0001f);
        b.dmin = (_Float16) (0.005f + (rng() % 100) * 0.00005f);
        for (int i = 0; i < 12; i++) b.scales[i] = (unsigned char) (rng() & 0x3F);
        for (int i = 0; i < 128; i++) b.qs[i] = (unsigned char) (rng() & 0xFF);
    }
    std::vector<float> x((size_t) M_TOK * K_DIM);
    for (auto & v : x) v = (float) ((int) (rng() % 2001) - 1000) / 500.0f;

    std::vector<signed char> xq8((size_t) M_TOK * K_DIM);
    std::vector<int> xq4((size_t) M_TOK * K_DIM / 8, 0), sa4((size_t) M_TOK * K_DIM / 8, 0),
                     sx8((size_t) M_TOK * K_DIM / 8, 0);
    std::vector<float> sc8((size_t) M_TOK * K_DIM / 32);
    for (int t = 0; t < M_TOK; t++) {
        for (int g = 0; g < K_DIM / 32; g++) {
            float mx = 0;
            for (int i = 0; i < 32; i++) mx = fmaxf(mx, fabsf(x[(size_t) t * K_DIM + g * 32 + i]));
            const float q8s = mx > 0 ? mx / 127.0f : 1.0f, q4s = mx > 0 ? mx / 7.0f : 1.0f;
            sc8[(size_t) t * (K_DIM / 32) + g] = q4s;
            for (int i = 0; i < 32; i++) {
                const int k = g * 32 + i;
                int v4 = (int) lrintf(x[(size_t) t * K_DIM + k] / q4s);
                if (v4 > 7) v4 = 7; if (v4 < -8) v4 = -8;
                xq8[(size_t) t * K_DIM + k] = (signed char) v4;
                xq4[(size_t) t * (K_DIM / 8) + k / 8] |= (v4 & 0xF) << (4 * (k % 8));
            }
        }
        for (int g8 = 0; g8 < K_DIM / 8; g8++) {
            int a = 0, b = 0;
            for (int i = 0; i < 8; i++) {
                a += (int) xq8[(size_t) t * K_DIM + g8 * 8 + i];
                int v = (xq4[(size_t) t * (K_DIM / 8) + g8] >> (4 * i)) & 0xF;
                if (v & 0x8) v -= 16;
                b += v;
            }
            sx8[(size_t) t * (K_DIM / 8) + g8] = a;
            sa4[(size_t) t * (K_DIM / 8) + g8] = b;
        }
    }

    // fp64 reference on QUANTIZED activations (isolate arithmetic from quantization)
    const int REF_T = 8;
    std::vector<double> ref((size_t) REF_T * N_ROWS, 0.0);
    for (int t = 0; t < REF_T; t++) for (int o = 0; o < N_ROWS; o++) {
        double a = 0;
        const BlockQ4K * wr = &w[(size_t) o * nblk];
        for (int kb = 0; kb < nblk; kb++) {
            const BlockQ4K * bl = wr + kb;
            const double d = (double) (float) bl->d, dmin = (double) (float) bl->dmin;
            for (int j = 0; j < 8; j++) {
                unsigned char sc, m; get_scale_min_k4(j, bl->scales, &sc, &m);
                for (int u = 0; u < 32; u++) {
                    const int k = kb * QK_K + j * 32 + u;
                    const int q = (u < 16) ? (bl->qs[16*j+u] & 0xF) : (bl->qs[16*j+u-16] >> 4);
                    a += (d * sc * q - dmin * m) * (double) (sc8[(size_t) t * K_DIM / 32 + k / 32] * (double) xq8[(size_t) t * K_DIM + k]);
                }
            }
        }
        ref[(size_t) t * N_ROWS + o] = a;
    }

    BlockQ4K * dw; signed char * dx8; int * dx4, *dsa4, *dsx8; float * ds8, *dy;
    hipMalloc(&dw, w.size() * sizeof(BlockQ4K));
    hipMalloc(&dx8, xq8.size()); hipMalloc(&dx4, xq4.size() * 4);
    hipMalloc(&dsa4, sa4.size() * 4); hipMalloc(&dsx8, sx8.size() * 4);
    hipMalloc(&ds8, sc8.size() * 4); hipMalloc(&dy, (size_t) M_TOK * N_ROWS * 4);
    hipMemcpy(dw, w.data(), w.size() * sizeof(BlockQ4K), hipMemcpyHostToDevice);
    hipMemcpy(dx8, xq8.data(), xq8.size(), hipMemcpyHostToDevice);
    hipMemcpy(dx4, xq4.data(), xq4.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(dsa4, sa4.data(), sa4.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(dsx8, sx8.data(), sx8.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(ds8, sc8.data(), sc8.size() * 4, hipMemcpyHostToDevice);

    const size_t shmem = nblk * sizeof(BlockQ4K) + 256;
    std::vector<float> yA((size_t) M_TOK * N_ROWS), yB(yA.size()), yC(yA.size());
    gemm_A_dp4a<<<N_ROWS, 256, shmem>>>(dw, dx8, dsx8, ds8, dy, K_DIM, 1);
    hipDeviceSynchronize(); hipMemcpy(yA.data(), dy, yA.size() * 4, hipMemcpyDeviceToHost);
    gemm_B_repack<<<N_ROWS, 256, shmem>>>(dw, dx8, ds8, dy, K_DIM, 1);
    hipDeviceSynchronize(); hipMemcpy(yB.data(), dy, yB.size() * 4, hipMemcpyDeviceToHost);
    gemm_C_packed<<<N_ROWS, 256, shmem>>>(dw, dx4, dsa4, ds8, dy, K_DIM, 1);
    hipDeviceSynchronize(); hipMemcpy(yC.data(), dy, yC.size() * 4, hipMemcpyDeviceToHost);
    printf("launch %s | %s | %s\n", hipGetErrorString(hipGetLastError()),
           hipGetErrorString(hipGetLastError()), hipGetErrorString(hipGetLastError()));

    long long ab = 0, ac = 0;
    for (size_t i = 0; i < yA.size(); i++) {
        if (memcmp(&yA[i], &yB[i], 4)) ab++;
        if (memcmp(&yA[i], &yC[i], 4)) ac++;
    }
    const double rA = ref_rel_l2(yA, ref, N_ROWS, REF_T);
    const double rB = ref_rel_l2(yB, ref, N_ROWS, REF_T);
    const double rC = ref_rel_l2(yC, ref, N_ROWS, REF_T);
    printf("P3 gate: bitwise A==B %lld/%zu  A==C %lld/%zu ; rel_l2 vs fp64ref A %.6f B %.6f C %.6f\n",
           ab, yA.size(), ac, yC.size(), rA, rB, rC);
    const bool p3ok = (ab == 0 && ac == 0);
    printf("P3 integer-identity: %s\n", p3ok ? "PASS" : "FAIL");

    // ================= microbench (interleaved trials) =================
    hipEvent_t e0, e1; hipEventCreate(&e0); hipEventCreate(&e1);
    std::vector<double> tA(trials), tB(trials), tC(trials);
    for (int tr = 0; tr < trials; tr++) {
        float ms;
        hipEventRecord(e0); gemm_A_dp4a<<<N_ROWS, 256, shmem>>>(dw, dx8, dsx8, ds8, dy, K_DIM, reps);
        hipEventRecord(e1); hipEventSynchronize(e1); hipEventElapsedTime(&ms, e0, e1); tA[tr] = ms;
        hipEventRecord(e0); gemm_B_repack<<<N_ROWS, 256, shmem>>>(dw, dx8, ds8, dy, K_DIM, reps);
        hipEventRecord(e1); hipEventSynchronize(e1); hipEventElapsedTime(&ms, e0, e1); tB[tr] = ms;
        hipEventRecord(e0); gemm_C_packed<<<N_ROWS, 256, shmem>>>(dw, dx4, dsa4, ds8, dy, K_DIM, reps);
        hipEventRecord(e1); hipEventSynchronize(e1); hipEventElapsedTime(&ms, e0, e1); tC[tr] = ms;
    }
    auto stat = [&](const std::vector<double> & t, double * mean, double * cv) {
        double m = 0; for (double v : t) m += v; m /= t.size();
        double s = 0; for (double v : t) s += (v - m) * (v - m);
        *mean = m; *cv = t.size() > 1 ? sqrt(s / (t.size() - 1)) / m : 0.0;
    };
    double mA, cA, mB, cB, mC, cC;
    stat(tA, &mA, &cA); stat(tB, &mB, &cB); stat(tC, &mC, &cC);
    const double mac = (double) reps * M_TOK * N_ROWS * K_DIM;
    printf("UBENCH A_dp4a  %.4f ms  %.3f TMAC/s  CV %.1f%%\n", mA, mac / (mA * 1e9), cA * 100);
    printf("UBENCH B_repack %.4f ms  %.3f TMAC/s  CV %.1f%%  vsA %.3fx\n", mB, mac / (mB * 1e9), cB * 100, mA / mB);
    printf("UBENCH C_packed %.4f ms  %.3f TMAC/s  CV %.1f%%  vsA %.3fx  vsB %.3fx\n",
           mC, mac / (mC * 1e9), cC * 100, mA / mC, mB / mC);
    printf("GATE microbench >=1.3x on P2-ideal arm C vs A: %s\n", (mA / mC >= 1.3) ? "PASS" : "FAIL");
    printf("GATE microbench >=1.3x on same-traffic arm B vs A: %s\n", (mA / mB >= 1.3) ? "PASS" : "FAIL");
    return 0;
}
