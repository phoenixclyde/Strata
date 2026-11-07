// dp4a / LDS ceiling probe for gfx906 (MI50).
//
// Answers three questions before touching MMQ:
//   1. what is the real v_dot4_i32_i8 throughput on this card (MAC/s)?
//   2. what is the LDS read bandwidth that the MMQ inner loop depends on (B/s)?
//   3. an MMQ-shaped loop (x from LDS, y in registers, 4 dp4a per x word)
//      runs at what fraction of (1)?
//
// Everything is deterministic: same inputs, same code path, MAC count is
// counted, not estimated.
#include <hip/hip_runtime.h>

#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x)                                                                     \
    do {                                                                          \
        hipError_t e_ = (x);                                                      \
        if (e_ != hipSuccess) {                                                   \
            std::printf("HIP error %s at %s:%d\n", hipGetErrorString(e_),         \
                        __FILE__, __LINE__);                                      \
            std::exit(1);                                                         \
        }                                                                         \
    } while (0)

__device__ __forceinline__ int dp4a(int a, int b, int c) {
#if defined(__gfx906__) || defined(__HIP_PLATFORM_AMD__)
    return __builtin_amdgcn_sdot4(a, b, c, false);
#else
    return __dp4a(a, b, c);
#endif
}

// 1) pure dp4a in registers: nothing but the instruction
__global__ void k_dp4a(int* out, int iters) {
    int a0 = threadIdx.x * 3 + 1, a1 = a0 ^ 0x1234, a2 = a0 + 7, a3 = a0 ^ 0x5555;
    int b0 = a0 + 1, b1 = a1 + 1, b2 = a2 + 1, b3 = a3 + 1;
    int s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (int i = 0; i < iters; ++i) {
        s0 = dp4a(a0, b0, s0);
        s1 = dp4a(a1, b1, s1);
        s2 = dp4a(a2, b2, s2);
        s3 = dp4a(a3, b3, s3);
        s0 = dp4a(a0, b1, s0);
        s1 = dp4a(a1, b2, s1);
        s2 = dp4a(a2, b3, s2);
        s3 = dp4a(a3, b0, s3);
    }
    if (s0 + s1 + s2 + s3 == 12345678) out[0] = s0;
}

// 2) LDS read bandwidth: each thread reads 4 B per iteration from LDS
__global__ void k_lds(int* out, int iters) {
    extern __shared__ int sm[];
    for (int i = threadIdx.x; i < 4096; i += blockDim.x) sm[i] = i * 7;
    __syncthreads();
    int s = 0;
    const int base = threadIdx.x;
    for (int i = 0; i < iters; ++i) {
        // 4 independent 4-byte LDS reads per iteration
        s += sm[(base + i * 4 + 0) & 4095];
        s += sm[(base + i * 4 + 1) & 4095];
        s += sm[(base + i * 4 + 2) & 4095];
        s += sm[(base + i * 4 + 3) & 4095];
    }
    if (s == 12345678) out[0] = s;
}

// 3) MMQ-shaped: x in LDS (one 4-byte word feeds 4 dp4a via the 4-bit unpack),
//    y in registers. This is what vec_dot_q4_K_q8_1_impl_mmq does per QR4_K.
__global__ void k_mmq_like(int* out, int iters) {
    extern __shared__ int sm[];
    for (int i = threadIdx.x; i < 4096; i += blockDim.x) sm[i] = 0x03020100 + i;
    __syncthreads();
    int u[4];
    u[0] = 0x01020304; u[1] = 0x05060708; u[2] = 0x090a0b0c; u[3] = 0x0d0e0f10;
    int acc = 0;
    const int base = threadIdx.x;
    for (int i = 0; i < iters; ++i) {
        const int v = sm[(base + i) & 4095];   // one LDS read, 4 B
#pragma unroll
        for (int k = 0; k < 4; ++k) {
            acc = dp4a((v >> (4 * k)) & 0x0F0F0F0F, u[k], acc);
        }
    }
    if (acc == 12345678) out[0] = acc;
}


// 4) MMQ-shaped but with the nibble unpack HOISTED out of the row loop:
//    unpack 4 words once, reuse them for J rows, ONE ACCUMULATOR PER ROW
//    (a single accumulator is latency-bound and measures nothing).
template <int J>
__global__ void k_mmq_hoist(int* out, int iters) {
    extern __shared__ int sm[];
    for (int i = threadIdx.x; i < 4096; i += blockDim.x) sm[i] = 0x03020100 + i;
    __syncthreads();
    int acc[J];
#pragma unroll
    for (int j = 0; j < J; ++j) acc[j] = 0;
    int u[4];
    u[0] = 0x01020304; u[1] = 0x05060708; u[2] = 0x090a0b0c; u[3] = 0x0d0e0f10;
    const int base = threadIdx.x;
    for (int it = 0; it < iters; ++it) {
        int xv[16];
#pragma unroll
        for (int w = 0; w < 4; ++w) {
            const int v = sm[(base + it * 4 + w) & 4095];
#pragma unroll
            for (int k = 0; k < 4; ++k) xv[w * 4 + k] = (v >> (4 * k)) & 0x0F0F0F0F;
        }
#pragma unroll
        for (int j = 0; j < J; ++j) {
#pragma unroll
            for (int m = 0; m < 16; ++m) acc[j] = dp4a(xv[m], u[m & 3] + j, acc[j]);
        }
    }
    int s = 0;
#pragma unroll
    for (int j = 0; j < J; ++j) s += acc[j];
    if (s == 12345678) out[0] = s;
}

static float bench(void (*kern)(int*, int), int blocks, int threads, int iters,
                   int smem, int macs_per_thread_iter) {
    int* d = nullptr;
    CK(hipMalloc(&d, sizeof(int)));
    // warm-up
    kern<<<blocks, threads, smem>>>(d, iters / 8);
    CK(hipDeviceSynchronize());

    hipEvent_t e0, e1;
    CK(hipEventCreate(&e0));
    CK(hipEventCreate(&e1));
    int reps = 5;
    CK(hipEventRecord(e0));
    for (int r = 0; r < reps; ++r) kern<<<blocks, threads, smem>>>(d, iters);
    CK(hipEventRecord(e1));
    CK(hipEventSynchronize(e1));
    float ms = 0;
    CK(hipEventElapsedTime(&ms, e0, e1));
    CK(hipFree(d));
    (void)macs_per_thread_iter;
    return ms / reps;
}

int main() {
    int nsm = 0;
    CK(hipDeviceGetAttribute(&nsm, hipDeviceAttributeMultiprocessorCount, 0));
    std::printf("CU=%d\n", nsm);

    const int blocks = nsm * 4;   // 4 blocks per CU
    const int threads = 256;
    const int iters = 20000;

    // ---- 1) dp4a peak: 8 dp4a per iteration per thread, 4 MACs each ----
    {
        float ms = bench(k_dp4a, blocks, threads, iters, 0, 32);
        double macs = (double) blocks * threads * iters * 8.0 * 4.0;
        std::printf("dp4a    : %.3f ms  -> %.2f TMAC/s (%.2f TFLOPS-eq)\n", ms,
                    macs / (ms * 1e-3) / 1e12, macs * 2 / (ms * 1e-3) / 1e12);
    }
    // ---- 2) LDS bandwidth: 4 reads of 4 B per iteration per thread ----
    {
        float ms = bench(k_lds, blocks, threads, iters, 16 * 1024, 16);
        double bytes = (double) blocks * threads * iters * 16.0;
        std::printf("LDS read: %.3f ms  -> %.1f GB/s\n", ms, bytes / (ms * 1e-3) / 1e9);
    }
    // ---- 3) MMQ-shaped: 1 LDS read + 4 dp4a per iteration ----
    {
        float ms = bench(k_mmq_like, blocks, threads, iters, 16 * 1024, 16);
        double macs = (double) blocks * threads * iters * 4.0 * 4.0;
        double bytes = (double) blocks * threads * iters * 4.0;
        std::printf("mmq-like: %.3f ms  -> %.2f TMAC/s, LDS %.1f GB/s\n", ms,
                    macs / (ms * 1e-3) / 1e12, bytes / (ms * 1e-3) / 1e9);
    }
    // ---- 4) hoisted unpack, J rows per unpack ----
    {
        const int J = 8;
        int* d = nullptr;
        CK(hipMalloc(&d, sizeof(int)));
        k_mmq_hoist<J><<<blocks, threads, 16 * 1024>>>(d, iters / 8);
        CK(hipDeviceSynchronize());
        hipEvent_t e0, e1;
        CK(hipEventCreate(&e0));
        CK(hipEventCreate(&e1));
        int reps = 5;
        CK(hipEventRecord(e0));
        for (int r = 0; r < reps; ++r) k_mmq_hoist<J><<<blocks, threads, 16 * 1024>>>(d, iters);
        CK(hipEventRecord(e1));
        CK(hipEventSynchronize(e1));
        float ms = 0;
        CK(hipEventElapsedTime(&ms, e0, e1));
        ms /= reps;
        double macs = (double) blocks * threads * iters * 16.0 * J * 4.0;
        std::printf("mmq-hoist(J=%d): %.3f ms -> %.2f TMAC/s\n", J,
                    macs / (ms * 1e-3) / 1e12);
        CK(hipFree(d));
    }
    return 0;
}
