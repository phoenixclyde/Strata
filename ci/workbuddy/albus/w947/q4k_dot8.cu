// W947 / R84: a REAL dot8 path for Q4_K — prototype kernel, measured against the dp4a path on the same data.
//
// Why a standalone prototype first: wiring int4 activations into the MMQ tile pipeline touches the LDS layout,
// the tile loader and the quantizer at once. This file proves the three things R84 actually needs, in isolation:
//   1. v_dot8_i32_i4 exists and is usable on this gfx906 toolchain (ISA + runtime),
//   2. the Q4_K <-> int4 math is exact enough (u4 ^ 0x8 == s4 q-8, so sum q*x = dot8 + 8*sum a),
//   3. the instruction win is real: one sdot8 replaces two dp4a per 8 values.
// Shape: one output row per warp, K = 2560, 1280 rows — the gate/up product of one expert.
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

struct BlockQ4K {
    _Float16 d;
    _Float16 dmin;
    unsigned char scales[12];
    unsigned char qs[128];
};
static_assert(sizeof(BlockQ4K) == 144, "block_q4_K is 144 bytes");

static __host__ __device__ void get_scale_min_k4(int j, const unsigned char * q, unsigned char * d, unsigned char * m) {
    if (j < 4) {
        *d = q[j] & 63;  *m = q[j + 4] & 63;
    } else {
        *d = (q[j + 4] & 0x0F) | ((q[j - 4] >> 6) << 4);
        *m = (q[j + 4] >> 4)   | ((q[j]     >> 6) << 4);
    }
}

// 8 consecutive values of one 32-value sub-block, packed as 8 nibbles (value i in nibble i).
// sub-block layout: values 0..15 = low nibbles of qs[0..15], 16..31 = high nibbles.
static __host__ __device__ inline unsigned pack8_u4(const unsigned char * qs16, int g) {
    unsigned r = 0;
    for (int i = 0; i < 8; i++) {
        const int idx = g * 8 + i;
        const unsigned v = (idx < 16) ? (qs16[idx] & 0xF) : (qs16[idx - 16] >> 4);
        r |= (v & 0xF) << (4 * i);
    }
    return r;
}

// ---- device ----

__device__ __forceinline__ int sdot4(int a, int b, int c) { return __builtin_amdgcn_sdot4(a, b, c, false); }
__device__ __forceinline__ int sdot8(int a, int b, int c) { return __builtin_amdgcn_sdot8(a, b, c, false); }

// One warp per output row. Each lane handles 8 consecutive values per iteration.
// x is pre-quantized: xq8 = int8 per value (dp4a path), xq4 = 8 int4 per int (dot8 path).
__global__ void q4k_gemv_dp4a(const BlockQ4K * __restrict__ w, const signed char * __restrict__ xq8,
                              const float * __restrict__ s8, float * __restrict__ y, int k) {
    const int row = blockIdx.x * (blockDim.x / 32) + (threadIdx.x / 32);
    const int lane = threadIdx.x & 31;
    if (row >= N_ROWS) return;
    const BlockQ4K * wr = w + (size_t) row * (k / QK_K);
    float acc = 0.0f;
    for (int base = lane * 8; base < k; base += 32 * 8) {
        const int kb = base / QK_K, kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
        const BlockQ4K * b = wr + kb;
        unsigned char sc, m;
        get_scale_min_k4(j, b->scales, &sc, &m);
        const unsigned q8 = pack8_u4(b->qs + 16 * j, g);          // 8 u4 values
        int sumi = 0;
        // two dp4a: low 4 values, high 4 values (as int8)
        for (int h = 0; h < 2; h++) {
            int vi = 0;
            for (int i = 0; i < 4; i++) vi |= (int) (((q8 >> (4 * (h * 4 + i))) & 0xF)) << (8 * i);
            int xi = 0;
            for (int i = 0; i < 4; i++) xi |= (int) ((unsigned char) xq8[base + h * 4 + i]) << (8 * i);
            sumi = sdot4(vi, xi, sumi);
        }
        int sx = 0;
        for (int i = 0; i < 8; i++) sx += (int) xq8[base + i];
        const float s = s8[base / 32];
        acc += (float) b->d * (float) sc * (s * (float) sumi) - (float) b->dmin * (float) m * (s * (float) sx);
    }
#pragma unroll
    for (int o = 16; o > 0; o >>= 1) acc += __shfl_down_sync(0xffffffffffffffffull, acc, o);
    if (lane == 0) y[row] = acc;
}

__global__ void q4k_gemv_dot8(const BlockQ4K * __restrict__ w, const int * __restrict__ xq4,
                              const float * __restrict__ s4, float * __restrict__ y, int k) {
    const int row = blockIdx.x * (blockDim.x / 32) + (threadIdx.x / 32);
    const int lane = threadIdx.x & 31;
    if (row >= N_ROWS) return;
    const BlockQ4K * wr = w + (size_t) row * (k / QK_K);
    float acc = 0.0f;
    for (int base = lane * 8; base < k; base += 32 * 8) {
        const int kb = base / QK_K, kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
        const BlockQ4K * b = wr + kb;
        unsigned char sc, m;
        get_scale_min_k4(j, b->scales, &sc, &m);
        const unsigned q8 = pack8_u4(b->qs + 16 * j, g);
        unsigned xs = (unsigned) xq4[base / 8];
        // sum of the 8 int4 activations (for the 8*sum(a) correction: u4 ^ 0x8 == s4 (q-8))
        int sa = 0;
        for (int i = 0; i < 8; i++) {
            int v = (int) ((xs >> (4 * i)) & 0xF);
            if (v & 0x8) v -= 16;
            sa += v;
        }
        const int sd = sdot8(q8 ^ 0x88888888u, xs, 0);  // sum (q-8)*a
        const int sumi = sd + 8 * sa;                   // sum q*a
        const float s = s4[base / 32];
        acc += (float) b->d * (float) sc * (s * (float) sumi) - (float) b->dmin * (float) m * (s * (float) sa);
    }
#pragma unroll
    for (int o = 16; o > 0; o >>= 1) acc += __shfl_down_sync(0xffffffffffffffffull, acc, o);
    if (lane == 0) y[row] = acc;
}

// ---- host ----

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
    std::vector<float> x(K_DIM);
    for (auto & v : x) v = (float) ((int) (rng() % 2001) - 1000) / 500.0f;

    // float reference
    std::vector<double> ref(N_ROWS, 0.0);
    for (int o = 0; o < N_ROWS; o++) {
        double a = 0;
        const BlockQ4K * wr = &w[(size_t) o * nblk];
        for (int kb = 0; kb < nblk; kb++) {
            const BlockQ4K * b = wr + kb;
            const double d = (double) (float) b->d, dmin = (double) (float) b->dmin;
            for (int j = 0; j < 8; j++) {
                unsigned char sc, m;
                get_scale_min_k4(j, b->scales, &sc, &m);
                for (int t = 0; t < 32; t++) {
                    const int k = kb * QK_K + j * 32 + t;
                    const int q = (t < 16) ? (b->qs[16 * j + t] & 0xF) : (b->qs[16 * j + t - 16] >> 4);
                    a += (d * sc * q - dmin * m) * (double) x[k];
                }
            }
        }
        ref[o] = a;
    }

    // quantize activations: int8 (per 32, symmetric) and int4 (per 32, symmetric)
    std::vector<signed char> xq8(K_DIM);
    std::vector<int> xq4(K_DIM / 8, 0);
    std::vector<float> sc8(K_DIM / 32), sc4(K_DIM / 32);
    for (int g = 0; g < K_DIM / 32; g++) {
        float mx = 0;
        for (int i = 0; i < 32; i++) mx = fmaxf(mx, fabsf(x[g * 32 + i]));
        const float s8 = mx > 0 ? mx / 127.0f : 1.0f;
        const float s4 = mx > 0 ? mx / 7.0f : 1.0f;
        sc8[g] = s8; sc4[g] = s4;
        for (int i = 0; i < 32; i++) {
            const int k = g * 32 + i;
            xq8[k] = (signed char) lrintf(x[k] / s8);
            int q = (int) lrintf(x[k] / s4);
            if (q > 7) q = 7;
            if (q < -8) q = -8;
            xq4[k / 8] |= (q & 0xF) << (4 * (k % 8));
        }
    }

    BlockQ4K * dw; signed char * dx8; int * dx4; float * dy; float * ds8; float * ds4;
    if (hipMalloc(&dw, w.size() * sizeof(BlockQ4K)) != hipSuccess) { printf("no device\n"); return 1; }
    hipMalloc(&dx8, K_DIM); hipMalloc(&dx4, (K_DIM / 8) * 4); hipMalloc(&dy, N_ROWS * 4);
    hipMalloc(&ds8, (K_DIM / 32) * 4); hipMalloc(&ds4, (K_DIM / 32) * 4);
    hipMemcpy(ds8, sc8.data(), (K_DIM / 32) * 4, hipMemcpyHostToDevice);
    hipMemcpy(ds4, sc4.data(), (K_DIM / 32) * 4, hipMemcpyHostToDevice);
    hipMemcpy(dw, w.data(), w.size() * sizeof(BlockQ4K), hipMemcpyHostToDevice);
    hipMemcpy(dx8, xq8.data(), K_DIM, hipMemcpyHostToDevice);
    hipMemcpy(dx4, xq4.data(), (K_DIM / 8) * 4, hipMemcpyHostToDevice);

    const int TPB = 256, WPB = TPB / 32;
    const int blocks = (N_ROWS + WPB - 1) / WPB;

    q4k_gemv_dp4a<<<blocks, TPB>>>(dw, dx8, ds8, dy, K_DIM);
    const hipError_t e1 = hipGetLastError();
    hipDeviceSynchronize();
    std::vector<float> y4a(N_ROWS);
    hipMemcpy(y4a.data(), dy, N_ROWS * 4, hipMemcpyDeviceToHost);

    q4k_gemv_dot8<<<blocks, TPB>>>(dw, dx4, ds4, dy, K_DIM);
    const hipError_t e2 = hipGetLastError();
    hipDeviceSynchronize();
    std::vector<float> y8(N_ROWS);
    hipMemcpy(y8.data(), dy, N_ROWS * 4, hipMemcpyDeviceToHost);

    printf("launch dp4a=%s dot8=%s\n", hipGetErrorString(e1), hipGetErrorString(e2));

    auto rel = [&](const std::vector<float> & y) {
        double n = 0, d = 0;
        for (int i = 0; i < N_ROWS; i++) { n += (y[i] - ref[i]) * (y[i] - ref[i]); d += ref[i] * ref[i]; }
        return sqrt(n / d);
    };
    printf("dp4a rel_l2 = %.5f\ndot8 rel_l2 = %.5f\n", rel(y4a), rel(y8));

    // timing
    const int rep = 50;
    hipEvent_t t0, t1; hipEventCreate(&t0); hipEventCreate(&t1);
    float ms4 = 0, ms8 = 0;
    hipEventRecord(t0);
    for (int i = 0; i < rep; i++) q4k_gemv_dp4a<<<blocks, TPB>>>(dw, dx8, ds8, dy, K_DIM);
    hipEventRecord(t1); hipEventSynchronize(t1); hipEventElapsedTime(&ms4, t0, t1);
    hipEventRecord(t0);
    for (int i = 0; i < rep; i++) q4k_gemv_dot8<<<blocks, TPB>>>(dw, dx4, ds4, dy, K_DIM);
    hipEventRecord(t1); hipEventSynchronize(t1); hipEventElapsedTime(&ms8, t0, t1);
    const double mac = (double) N_ROWS * K_DIM;
    printf("dp4a  %.3f ms  %.2f TMAC/s\ndot8  %.3f ms  %.2f TMAC/s\nspeedup %.3f x\n",
           ms4 / rep, mac / (ms4 / rep * 1e9), ms8 / rep, mac / (ms8 / rep * 1e9), ms4 / ms8);
    return 0;
}
