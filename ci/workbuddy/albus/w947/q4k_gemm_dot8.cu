// W947 / R84 take 2: M=64 GEMM shape (not GEMV) — at M=1 the weight stream dominates and both dot paths
// collapse to the same bandwidth-bound time. Real target: one expert's gate/up, 1280 rows x 2560 K x 64 tokens.
// Integer sums are precomputed by the quantizer on both sides so neither path pays for them inside the loop.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <random>

#define QK_K 256
#define K_DIM 2560
#define N_ROWS 1280
#define M_TOK  64
#define TPW    8          /* tokens per warp = M_TOK / 8 warps */

struct BlockQ4K {
    _Float16 d;
    _Float16 dmin;
    unsigned char scales[12];
    unsigned char qs[128];
};

static __host__ __device__ inline void get_scale_min_k4(int j, const unsigned char * q, unsigned char * d, unsigned char * m) {
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

// y[token * N_ROWS + row]
__global__ void q4k_gemm_dp4a(const BlockQ4K * __restrict__ w, const signed char * __restrict__ xq8,
                              const int * __restrict__ sx8, const float * __restrict__ s8,
                              float * __restrict__ y, int k) {
    const int row = blockIdx.x, lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    const int t0 = warp * TPW;
    float acc[TPW];
#pragma unroll
    for (int i = 0; i < TPW; i++) acc[i] = 0.0f;
    const BlockQ4K * wr = w + (size_t) row * (k / QK_K);
    for (int base = lane * 8; base < k; base += 32 * 8) {
        const BlockQ4K * b = wr + base / QK_K;
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
    // warp reduction — without it the 32 lanes overwrite each other and y ends up 1/32 of the truth
    const int lane_ = threadIdx.x & 31;
#pragma unroll
    for (int t = 0; t < TPW; t++) {
        float v = acc[t];
#pragma unroll
        for (int o = 16; o > 0; o >>= 1) v += __shfl_down_sync(0xffffffffffffffffull, v, o);
        if (lane_ == 0) y[(size_t) (t0 + t) * N_ROWS + row] = v;
    }
}

__global__ void q4k_gemm_dot8(const BlockQ4K * __restrict__ w, const int * __restrict__ xq4,
                              const int * __restrict__ sa4, const float * __restrict__ s4,
                              float * __restrict__ y, int k) {
    const int row = blockIdx.x, lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    const int t0 = warp * TPW;
    float acc[TPW];
#pragma unroll
    for (int i = 0; i < TPW; i++) acc[i] = 0.0f;
    const BlockQ4K * wr = w + (size_t) row * (k / QK_K);
    for (int base = lane * 8; base < k; base += 32 * 8) {
        const BlockQ4K * b = wr + base / QK_K;
        const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
        unsigned char sc, m;
        get_scale_min_k4(j, b->scales, &sc, &m);
        const int qx = (int) (pack8_u4(b->qs + 16 * j, g) ^ 0x88888888u);
        const float dm_d = (float) b->d * (float) sc, dm_m = (float) b->dmin * (float) m;
#pragma unroll
        for (int t = 0; t < TPW; t++) {
            const int tok = t0 + t;
            const int xs = xq4[(size_t) tok * (k / 8) + base / 8];
            const int sa = sa4[(size_t) tok * (k / 8) + base / 8];
            const int sd = sdot8(qx, xs, 0);          // sum (q-8)*a
            const int sumi = sd + 8 * sa;             // sum q*a
            const float s = s4[(size_t) tok * (k / 32) + base / 32];
            acc[t] += dm_d * (s * (float) sumi) - dm_m * (s * (float) sa);
        }
    }
    // warp reduction — without it the 32 lanes overwrite each other and y ends up 1/32 of the truth
    const int lane_ = threadIdx.x & 31;
#pragma unroll
    for (int t = 0; t < TPW; t++) {
        float v = acc[t];
#pragma unroll
        for (int o = 16; o > 0; o >>= 1) v += __shfl_down_sync(0xffffffffffffffffull, v, o);
        if (lane_ == 0) y[(size_t) (t0 + t) * N_ROWS + row] = v;
    }
}

int main() {
    std::mt19937 rng(947);
    const int nblk = K_DIM / QK_K;
    std::vector<BlockQ4K> w((size_t) N_ROWS * nblk);
    for (auto & b : w) {
        b.d = (_Float16) (0.01f + (rng() % 100) * 0.0001f);
        b.dmin = (_Float16) (0.005f + (rng() % 100) * 0.00005f);
        for (int i = 0; i < 12; i++) b.scales[i] = (unsigned char) (rng() & 0xFF);
        for (int i = 0; i < 128; i++) b.qs[i] = (unsigned char) (rng() & 0xFF);
    }
    std::vector<float> x((size_t) M_TOK * K_DIM);
    for (auto & v : x) v = (float) ((int) (rng() % 2001) - 1000) / 500.0f;

    std::vector<signed char> xq8((size_t) M_TOK * K_DIM);
    std::vector<int> xq4((size_t) M_TOK * K_DIM / 8, 0), sx8((size_t) M_TOK * K_DIM / 8, 0), sa4((size_t) M_TOK * K_DIM / 8, 0);
    std::vector<float> sc8((size_t) M_TOK * K_DIM / 32), sc4((size_t) M_TOK * K_DIM / 32);
    for (int t = 0; t < M_TOK; t++) {
        for (int g = 0; g < K_DIM / 32; g++) {
            float mx = 0;
            for (int i = 0; i < 32; i++) mx = fmaxf(mx, fabsf(x[(size_t) t * K_DIM + g * 32 + i]));
            const float q8s = mx > 0 ? mx / 127.0f : 1.0f, q4s = mx > 0 ? mx / 7.0f : 1.0f;
            sc8[(size_t) t * (K_DIM / 32) + g] = q8s;
            sc4[(size_t) t * (K_DIM / 32) + g] = q4s;
            for (int i = 0; i < 32; i++) {
                const int k = g * 32 + i;
                const int v8 = (int) lrintf(x[(size_t) t * K_DIM + k] / q8s);
                xq8[(size_t) t * K_DIM + k] = (signed char) v8;
                int v4 = (int) lrintf(x[(size_t) t * K_DIM + k] / q4s);
                if (v4 > 7) v4 = 7;
                if (v4 < -8) v4 = -8;
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

    // float reference for 8 of the 64 tokens (enough for a rel_l2)
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
                    a += (d * sc * q - dmin * m) * (double) x[(size_t) t * K_DIM + k];
                }
            }
        }
        ref[(size_t) t * N_ROWS + o] = a;
    }

    // ---- host simulation of the dp4a kernel (token 0, row 0), same formula, no GPU ----
    {
        double sim = 0.0;
        const BlockQ4K * wr = &w[0];
        for (int base = 0; base < K_DIM; base += 8) {
            const BlockQ4K * b = wr + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m; get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned q8 = pack8_u4(b->qs + 16 * j, g);
            int sumi = 0;
            for (int i = 0; i < 8; i++) sumi += (int) ((q8 >> (4 * i)) & 0xF) * (int) xq8[base + i];
            const float s = sc8[base / 32];
            const int sx = sx8[base / 8];
            sim += (double) ((float) b->d * sc * (s * (float) sumi) - (float) b->dmin * m * (s * (float) sx));
        }
        printf("HOST-SIM (token0,row0) = %.6f   fp32-ref = %.6f   ratio = %.6f\n",
               sim, ref[0], ref[0] != 0 ? sim / ref[0] : 0.0);

        // and the same for the dot8 path
        double sim8 = 0.0;
        for (int base = 0; base < K_DIM; base += 8) {
            const BlockQ4K * b = wr + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m; get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned qx = pack8_u4(b->qs + 16 * j, g) ^ 0x88888888u;
            int sd = 0;
            for (int i = 0; i < 8; i++) {
                const int q = (int) ((qx >> (4 * i)) & 0xF);
                const int qs4 = (q >= 8) ? q - 16 : q;          // s4 interpretation
                const int xa = (int) ((xq4[base / 8] >> (4 * i)) & 0xF);
                const int xs4 = (xa >= 8) ? xa - 16 : xa;
                sd += qs4 * xs4;
            }
            const int sa = sa4[base / 8];
            const int sumi = sd + 8 * sa;
            const float s = sc4[base / 32];
            sim8 += (double) ((float) b->d * sc * (s * (float) sumi) - (float) b->dmin * m * (s * (float) sa));
        }
        printf("HOST-SIM-DOT8 (token0,row0) = %.6f   fp32-ref = %.6f   ratio = %.6f\n",
               sim8, ref[0], ref[0] != 0 ? sim8 / ref[0] : 0.0);
    }

    BlockQ4K * dw; signed char * dx8; int * dx4, *dsx8, *dsa4; float * ds8, *ds4, *dy;
    if (hipMalloc(&dw, w.size() * sizeof(BlockQ4K)) != hipSuccess) { printf("no device\n"); return 1; }
    hipMalloc(&dx8, xq8.size()); hipMalloc(&dx4, xq4.size() * 4);
    hipMalloc(&dsx8, sx8.size() * 4); hipMalloc(&dsa4, sa4.size() * 4);
    hipMalloc(&ds8, sc8.size() * 4); hipMalloc(&ds4, sc4.size() * 4);
    hipMalloc(&dy, (size_t) M_TOK * N_ROWS * 4);
    hipMemcpy(dw, w.data(), w.size() * sizeof(BlockQ4K), hipMemcpyHostToDevice);
    hipMemcpy(dx8, xq8.data(), xq8.size(), hipMemcpyHostToDevice);
    hipMemcpy(dx4, xq4.data(), xq4.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(dsx8, sx8.data(), sx8.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(dsa4, sa4.data(), sa4.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(ds8, sc8.data(), sc8.size() * 4, hipMemcpyHostToDevice);
    hipMemcpy(ds4, sc4.data(), sc4.size() * 4, hipMemcpyHostToDevice);

    std::vector<float> y((size_t) M_TOK * N_ROWS);
    q4k_gemm_dp4a<<<N_ROWS, 256>>>(dw, dx8, dsx8, ds8, dy, K_DIM);
    const hipError_t e1 = hipGetLastError();
    hipDeviceSynchronize();
    hipMemcpy(y.data(), dy, y.size() * 4, hipMemcpyDeviceToHost);
    double n8 = 0, dd = 0;
    for (int t = 0; t < REF_T; t++) for (int o = 0; o < N_ROWS; o++) {
        const double a = y[(size_t) t * N_ROWS + o], b = ref[(size_t) t * N_ROWS + o];
        n8 += (a - b) * (a - b); dd += b * b;
    }
    const double r8 = sqrt(n8 / dd);

    q4k_gemm_dot8<<<N_ROWS, 256>>>(dw, dx4, dsa4, ds4, dy, K_DIM);
    const hipError_t e2 = hipGetLastError();
    hipDeviceSynchronize();
    hipMemcpy(y.data(), dy, y.size() * 4, hipMemcpyDeviceToHost);
    double n4 = 0;
    for (int t = 0; t < REF_T; t++) for (int o = 0; o < N_ROWS; o++) {
        const double a = y[(size_t) t * N_ROWS + o], b = ref[(size_t) t * N_ROWS + o];
        n4 += (a - b) * (a - b);
    }
    const double r4 = sqrt(n4 / dd);
    printf("launch dp4a=%s dot8=%s\n", hipGetErrorString(e1), hipGetErrorString(e2));
    printf("M=%d  dp4a rel_l2 = %.5f   dot8 rel_l2 = %.5f  (vs fp32, same weights)\n", M_TOK, r8, r4);

    const int rep = 30;
    hipEvent_t a, b; hipEventCreate(&a); hipEventCreate(&b);
    float ms4 = 0, ms8 = 0;
    hipEventRecord(a);
    for (int i = 0; i < rep; i++) q4k_gemm_dp4a<<<N_ROWS, 256>>>(dw, dx8, dsx8, ds8, dy, K_DIM);
    hipEventRecord(b); hipEventSynchronize(b); hipEventElapsedTime(&ms4, a, b);
    hipEventRecord(a);
    for (int i = 0; i < rep; i++) q4k_gemm_dot8<<<N_ROWS, 256>>>(dw, dx4, dsa4, ds4, dy, K_DIM);
    hipEventRecord(b); hipEventSynchronize(b); hipEventElapsedTime(&ms8, a, b);
    const double mac = (double) M_TOK * N_ROWS * K_DIM;
    printf("dp4a  %.3f ms  %.2f TMAC/s\ndot8  %.3f ms  %.2f TMAC/s\nspeedup %.3f x\n",
           ms4 / rep, mac / (ms4 / rep * 1e9), ms8 / rep, mac / (ms8 / rep * 1e9), ms4 / ms8);
    return 0;
}
