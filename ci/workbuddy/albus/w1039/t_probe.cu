// W1039/P457 probe: does the manual K read + late scale produce the same per-lane partial as load8_q8?
// Standalone (no engine, no config, no window): a few MB of synthetic pool, one kernel launch, printf to stdout.
// That channel is the point -- device printf inside the numeric gate is swallowed by the harness (P462),
// and a standalone program prints fine.
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdio>
#include <cstdint>
#include <cstdlib>

constexpr int HD = 256;
constexpr int GROUP = 64;              // KV_Q8_GROUP
constexpr int NSC = HD / GROUP;        // scales per row

struct Pools {
    const int8_t* k_q;
    const uint16_t* k_scale;
};

__device__ __forceinline__ void load8_q8(const Pools& p, long long row, int d0, float* out) {
    const int8_t* codes = p.k_q + row * HD + d0;
    const uint16_t sbits = p.k_scale[row * (HD / GROUP) + d0 / GROUP];
    const float sc = __half2float(__ushort_as_half(sbits));
    const uint2 raw = *reinterpret_cast<const uint2*>(codes);
    const int8_t* c = reinterpret_cast<const int8_t*>(&raw);
#pragma unroll
    for (int j = 0; j < 8; ++j) out[j] = (float) c[j] * sc;
}

__global__ void probe(const Pools p, const float* q, float* sref, float* sman, float* kmax) {
    const int lane = threadIdx.x & 31;
    const long long row = blockIdx.x;

    // (a) the 8 K values, two ways
    float k8[8];
    load8_q8(p, row, lane * 8, k8);

    const uint2 kraw = *reinterpret_cast<const uint2*>(p.k_q + row * HD + lane * 8);
    const float ks = __half2float(__ushort_as_half(p.k_scale[row * NSC + (lane * 8) / GROUP]));
    const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);

    // (b) per-lane partial for one head, both ways (same q, same expression shape, fp32 fma)
    const float4 qa = *reinterpret_cast<const float4*>(&q[lane * 8]);
    const float4 qb = *reinterpret_cast<const float4*>(&q[lane * 8 + 4]);
    const float a1 = k8[0] * qa.x + k8[1] * qa.y + k8[2] * qa.z + k8[3] * qa.w +
                     k8[4] * qb.x + k8[5] * qb.y + k8[6] * qb.z + k8[7] * qb.w;
    const float pp = (float) kb[0] * qa.x + (float) kb[1] * qa.y + (float) kb[2] * qa.z +
                     (float) kb[3] * qa.w + (float) kb[4] * qb.x + (float) kb[5] * qb.y +
                     (float) kb[6] * qb.z + (float) kb[7] * qb.w;
    const float a2 = pp * ks;

    sref[row * 32 + lane] = a1;
    sman[row * 32 + lane] = a2;

    // (c) the 32-lane reduction, both ways, same butterfly
    float r1 = a1, r2 = a2;
#pragma unroll
    for (int off = 16; off > 0; off >>= 1) {
        r1 += __shfl_xor(r1, off);
        r2 += __shfl_xor(r2, off);
    }
    if (lane == 0) {
        sref[row * 32 + 31] += 0.0f;                 // keep the store pattern simple
        kmax[row * 2 + 0] = r1;
        kmax[row * 2 + 1] = r2;
    }

    if (row == 0 && (lane == 0 || lane == 8)) {
        printf("row=%lld lane=%2d ks=%.9g codes=[%d %d %d %d %d %d %d %d] "
               "load8=[%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f]\n",
               row, lane, ks, (int) kb[0], (int) kb[1], (int) kb[2], (int) kb[3],
               (int) kb[4], (int) kb[5], (int) kb[6], (int) kb[7],
               k8[0], k8[1], k8[2], k8[3], k8[4], k8[5], k8[6], k8[7]);
        printf("        partial: baseline=%.9g  manual=%.9g  rel=%.3g\n",
               a1, a2, fabsf(a1 - a2) / (fabsf(a1) + 1e-30f));
        printf("        score  : baseline=%.9g  manual=%.9g  rel=%.3g\n",
               r1, r2, fabsf(r1 - r2) / (fabsf(r1) + 1e-30f));
    }
}

int main() {
    const int rows = 64;
    int8_t* d_k = nullptr;
    uint16_t* d_s = nullptr;
    float *d_q = nullptr, *d_ref = nullptr, *d_man = nullptr, *d_sc = nullptr;
    hipMalloc(&d_k, rows * HD);
    hipMalloc(&d_s, rows * NSC * sizeof(uint16_t));
    hipMalloc(&d_q, HD * sizeof(float));
    hipMalloc(&d_ref, rows * 32 * sizeof(float));
    hipMalloc(&d_man, rows * 32 * sizeof(float));
    hipMalloc(&d_sc, rows * 2 * sizeof(float));

    srand(7);
    int8_t* h_k = (int8_t*) malloc(rows * HD);
    uint16_t* h_s = (uint16_t*) malloc(rows * NSC * sizeof(uint16_t));
    float* h_q = (float*) malloc(HD * sizeof(float));
    for (int i = 0; i < rows * HD; ++i) h_k[i] = (int8_t) ((rand() % 255) - 127);
    for (int i = 0; i < rows * NSC; ++i) {
        float v = 0.0015f + 0.002f * (rand() / (float) RAND_MAX);
        __half h = __float2half(v);
        h_s[i] = *reinterpret_cast<uint16_t*>(&h);
    }
    for (int i = 0; i < HD; ++i) h_q[i] = 0.5f * ((rand() / (float) RAND_MAX) - 0.5f);

    hipMemcpy(d_k, h_k, rows * HD, hipMemcpyHostToDevice);
    hipMemcpy(d_s, h_s, rows * NSC * sizeof(uint16_t), hipMemcpyHostToDevice);
    hipMemcpy(d_q, h_q, HD * sizeof(float), hipMemcpyHostToDevice);

    Pools p{d_k, d_s};
    probe<<<rows, 32>>>(p, d_q, d_ref, d_man, d_sc);
    printf("launch rc=%d\n", (int) hipDeviceSynchronize());

    float* h_ref = (float*) malloc(rows * 32 * sizeof(float));
    float* h_man = (float*) malloc(rows * 32 * sizeof(float));
    float* h_sc = (float*) malloc(rows * 2 * sizeof(float));
    hipMemcpy(h_ref, d_ref, rows * 32 * sizeof(float), hipMemcpyDeviceToHost);
    hipMemcpy(h_man, d_man, rows * 32 * sizeof(float), hipMemcpyDeviceToHost);
    hipMemcpy(h_sc, d_sc, rows * 2 * sizeof(float), hipMemcpyDeviceToHost);

    float maxd = 0.0f, maxrel = 0.0f;
    int ndiff = 0;
    for (int i = 0; i < rows * 32; ++i) {
        float d = fabsf(h_ref[i] - h_man[i]);
        if (d > 0.0f) ++ndiff;
        if (d > maxd) maxd = d;
        float rel = d / (fabsf(h_ref[i]) + 1e-30f);
        if (rel > maxrel) maxrel = rel;
    }
    float maxs = 0.0f;
    for (int r = 0; r < rows; ++r) {
        float d = fabsf(h_sc[2 * r] - h_sc[2 * r + 1]);
        if (d > maxs) maxs = d;
    }
    printf("\nper-lane partials: %d pairs, differing %d, max|d| %.6g, max rel %.3g\n",
           rows * 32, ndiff, maxd, maxrel);
    printf("32-lane scores   : max|d| %.6g\n", maxs);
    printf("VERDICT: %s\n", (ndiff == 0) ? "BIT-IDENTICAL (the manual read and the late scale are exact)"
                                           : "DIFFERENT (the manual read or the scale index is wrong)");
    return 0;
}
