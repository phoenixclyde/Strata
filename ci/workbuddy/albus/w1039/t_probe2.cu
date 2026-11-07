// W1039/P457 probe #2: does the fp32 association difference grow when the 8-term dot nearly cancels?
//
// Probe #1 used random q and k and got max|d| = 3e-08 on the partial.  But the real model's queries may sit
// far from zero while the K codes sum to ~0, i.e. massive cancellation: sum|c*q| >> |sum c*q|.  A relative
// error of 1e-7 on the TERMS then becomes a much larger relative error on the SUM.  This probe measures that
// amplification instead of assuming it, on two workloads: "random" and "near-cancelling".
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cmath>

constexpr int HD = 256;
constexpr int GROUP = 64;
constexpr int NSC = HD / GROUP;

struct Pools { const int8_t* k_q; const uint16_t* k_scale; };

__device__ __forceinline__ void load8_q8(const Pools& p, long long row, int d0, float* out) {
    const int8_t* codes = p.k_q + row * HD + d0;
    const uint16_t sbits = p.k_scale[row * (HD / GROUP) + d0 / GROUP];
    const float sc = __half2float(__ushort_as_half(sbits));
    const uint2 raw = *reinterpret_cast<const uint2*>(codes);
    const int8_t* c = reinterpret_cast<const int8_t*>(&raw);
#pragma unroll
    for (int j = 0; j < 8; ++j) out[j] = (float) c[j] * sc;
}

// one row, warp of 32 lanes, head 0 only; writes baseline/manual partials and the two 32-lane sums
__global__ void probe(const Pools p, const float* q, float* par_ref, float* par_man, float* sc_out) {
    const int lane = threadIdx.x & 31;
    const long long row = blockIdx.x;

    float k8[8];
    load8_q8(p, row, lane * 8, k8);

    const uint2 kraw = *reinterpret_cast<const uint2*>(p.k_q + row * HD + lane * 8);
    const float ks = __half2float(__ushort_as_half(p.k_scale[row * NSC + (lane * 8) / GROUP]));
    const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);

    const float4 qa = *reinterpret_cast<const float4*>(&q[lane * 8]);
    const float4 qb = *reinterpret_cast<const float4*>(&q[lane * 8 + 4]);

    const float a1 = k8[0] * qa.x + k8[1] * qa.y + k8[2] * qa.z + k8[3] * qa.w +
                     k8[4] * qb.x + k8[5] * qb.y + k8[6] * qb.z + k8[7] * qb.w;
    const float pp = (float) kb[0] * qa.x + (float) kb[1] * qa.y + (float) kb[2] * qa.z +
                     (float) kb[3] * qa.w + (float) kb[4] * qb.x + (float) kb[5] * qb.y +
                     (float) kb[6] * qb.z + (float) kb[7] * qb.w;
    const float a2 = pp * ks;

    par_ref[row * 32 + lane] = a1;
    par_man[row * 32 + lane] = a2;

    float r1 = a1, r2 = a2;
#pragma unroll
    for (int off = 16; off > 0; off >>= 1) { r1 += __shfl_xor(r1, off); r2 += __shfl_xor(r2, off); }
    if (lane == 0) { sc_out[row * 2] = r1; sc_out[row * 2 + 1] = r2; }
}

static void run_case(const char* tag, int rows, int mode) {
    int8_t* h_k = (int8_t*) malloc(rows * HD);
    uint16_t* h_s = (uint16_t*) malloc(rows * NSC * sizeof(uint16_t));
    float* h_q = (float*) malloc(HD * sizeof(float));
    srand(11);
    if (mode == 0) {                        // random, like probe #1
        for (int i = 0; i < rows * HD; ++i) h_k[i] = (int8_t) ((rand() % 255) - 127);
        for (int i = 0; i < HD; ++i) h_q[i] = 0.5f * ((rand() / (float) RAND_MAX) - 0.5f);
    } else {                                // near-cancelling: codes balanced +- within each row, q with a big DC
        for (int r = 0; r < rows; ++r) {
            for (int d = 0; d < HD; ++d) {
                int sgn = (d & 1) ? -1 : 1;
                h_k[r * HD + d] = (int8_t) (sgn * (60 + rand() % 60));
            }
        }
        for (int i = 0; i < HD; ++i) h_q[i] = 8.0f + 0.02f * ((rand() / (float) RAND_MAX) - 0.5f);
    }
    for (int i = 0; i < rows * NSC; ++i) {
        float v = 0.0015f + 0.002f * (rand() / (float) RAND_MAX);
        __half h = __float2half(v);
        h_s[i] = *reinterpret_cast<uint16_t*>(&h);
    }

    int8_t *d_k; uint16_t *d_s; float *d_q, *d_pr, *d_pm, *d_sc;
    hipMalloc(&d_k, rows * HD); hipMalloc(&d_s, rows * NSC * sizeof(uint16_t));
    hipMalloc(&d_q, HD * sizeof(float));
    hipMalloc(&d_pr, rows * 32 * sizeof(float)); hipMalloc(&d_pm, rows * 32 * sizeof(float));
    hipMalloc(&d_sc, rows * 2 * sizeof(float));
    hipMemcpy(d_k, h_k, rows * HD, hipMemcpyHostToDevice);
    hipMemcpy(d_s, h_s, rows * NSC * sizeof(uint16_t), hipMemcpyHostToDevice);
    hipMemcpy(d_q, h_q, HD * sizeof(float), hipMemcpyHostToDevice);

    Pools p{d_k, d_s};
    probe<<<rows, 32>>>(p, d_q, d_pr, d_pm, d_sc);
    hipDeviceSynchronize();

    float* hr = (float*) malloc(rows * 32 * sizeof(float));
    float* hm = (float*) malloc(rows * 32 * sizeof(float));
    float* hs = (float*) malloc(rows * 2 * sizeof(float));
    hipMemcpy(hr, d_pr, rows * 32 * sizeof(float), hipMemcpyDeviceToHost);
    hipMemcpy(hm, d_pm, rows * 32 * sizeof(float), hipMemcpyDeviceToHost);
    hipMemcpy(hs, d_sc, rows * 2 * sizeof(float), hipMemcpyDeviceToHost);

    double maxabs = 0.0, maxrel = 0.0, sumabs = 0.0, sumval = 0.0;
    int ndiff = 0;
    for (int i = 0; i < rows * 32; ++i) {
        double d = fabs((double) hr[i] - (double) hm[i]);
        if (d > 0) ++ndiff;
        if (d > maxabs) maxabs = d;
        double rel = d / (fabs((double) hr[i]) + 1e-30);
        if (rel > maxrel) maxrel = rel;
        sumabs += fabs((double) hr[i]);
        sumval += (double) hr[i];
    }
    double smax = 0.0, srel = 0.0;
    for (int r = 0; r < rows; ++r) {
        double d = fabs((double) hs[2 * r] - (double) hs[2 * r + 1]);
        if (d > smax) smax = d;
        double rel = d / (fabs((double) hs[2 * r]) + 1e-30);
        if (rel > srel) srel = rel;
    }
    printf("\n== %s ==\n", tag);
    printf("  partials : %d/%d differ, max|d| %.4g, max rel %.4g\n", ndiff, rows * 32, maxabs, maxrel);
    printf("  sum|c*q| / |sum c*q| (cancellation factor) = %.1f\n", sumabs / (fabs(sumval) + 1e-30));
    printf("  score    : max|d| %.4g, max rel %.4g\n", smax, srel);

    free(h_k); free(h_s); free(h_q); free(hr); free(hm); free(hs);
    hipFree(d_k); hipFree(d_s); hipFree(d_q); hipFree(d_pr); hipFree(d_pm); hipFree(d_sc);
}

int main() {
    run_case("random q/k (as probe #1)", 64, 0);
    run_case("near-cancelling q/k (q DC=8, codes balanced)", 64, 1);
    return 0;
}
