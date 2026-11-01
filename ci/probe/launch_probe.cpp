// Launch-granularity probe: is the HC read slow because the kernel is slow, or because there are
// 48 tiny kernels per token?
//
// THE QUESTION
// ------------
// R22 counted the HC weights at 644 MiB over four matrices and 48 layers, i.e. 3.5 MB per
// (layer, matrix). Production spends 3.46 ms on the two `down` matrices per window:
//
//     3.46 ms / (2 matrices * 48 layers) = 36 us per 3.5 MB  ->  97 GB/s
//
// A probe reading the same 3.5 MB shape with the work batched into one launch reaches 664 GB/s.
// Same bytes, same arithmetic, 6.8x apart. The difference in shape is that production issues
// one small kernel per layer while the probe amortises the launch across many passes.
//
// So this probe holds the TOTAL BYTES FIXED and only varies how many launches it takes to read
// them:
//
//     rep=1   -> 256 launches of 3.5 MB   (production's shape)
//     rep=64  ->   4 launches of 224 MB   (fully batched)
//
// If bandwidth climbs with rep, the cost is per-launch overhead, and the fix is to fuse work
// across layers (persistent kernel / batched multi-tensor launch) -- NOT to touch the kernel.
// If bandwidth is flat, the cost is inside the kernel and R32's original direction stands.
//
// METHOD NOTES (each of these bit me before; see read_probe.cpp / rs_probe.cpp headers)
//   * every pass reads a DIFFERENT copy, so no pass sees bytes an earlier pass pulled into L2;
//   * the block stores a data-dependent reduction, so no load can be optimised away;
//   * the activation tile lives in registers, so no per-block LDS fill is charged to the timing.
//
// Build: hipcc --offload-arch=gfx906 -O3 -o launch_probe launch_probe.cpp
// Run:   ./launch_probe

#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>

#define CHECK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    printf("HIP error %s at %s:%d\n", hipGetErrorString(e), __FILE__, __LINE__); exit(1); } } while (0)

__device__ inline float gemv_block_fma(const unsigned char* p, const float* x) {
    union { unsigned short u; __half h; } cv;
    cv.u = *(const unsigned short*)p;
    const float d = __half2float(cv.h);
    float s = 0.f;
    #pragma unroll
    for (int i = 0; i < 16; ++i) {
        const unsigned short two = *(const unsigned short*)(p + 2 + 2 * i);
        s = fmaf((float)(int)(signed char)(two & 0xFF),        x[2 * i],     s);
        s = fmaf((float)(int)(signed char)((two >> 8) & 0xFF), x[2 * i + 1], s);
    }
    return d * s;
}

// Reads `rep` different copies of one (n_in -> n_out) Q8_0 matrix.
__global__ void read_kernel(const unsigned char* __restrict__ w, int nblk, int n_out,
                            size_t copy_stride, int start_copy, int rep,
                            float* __restrict__ out) {
    const int row = blockIdx.x;

    float xr[32];
    #pragma unroll
    for (int i = 0; i < 32; ++i) xr[i] = (float)((i + threadIdx.x) & 7) * 0.125f;

    float facc = 0.f;
    for (int t = 0; t < rep; ++t) {
        const unsigned char* rowp = w + (size_t)(start_copy + t) * copy_stride
                                      + (size_t)row * (size_t)nblk * 34u;
        for (int b = threadIdx.x; b < nblk; b += blockDim.x)
            facc += gemv_block_fma(rowp + (size_t)b * 34u, xr);
    }

    unsigned int acc = __float_as_uint(facc);
    __shared__ unsigned int red[256];
    red[threadIdx.x] = acc;
    __syncthreads();
    for (int off = blockDim.x / 2; off > 0; off >>= 1) {
        if (threadIdx.x < off) red[threadIdx.x] ^= red[threadIdx.x + off];
        __syncthreads();
    }
    if (threadIdx.x == 0) out[(blockIdx.x + start_copy) & 1023] = (float)red[0];
}

int main() {
    hipDeviceProp_t p{};
    CHECK(hipGetDeviceProperties(&p, 0));
    size_t freeB = 0, totalB = 0;
    CHECK(hipMemGetInfo(&freeB, &totalB));
    printf("device: %s  CUs=%d  free %.0f MiB\n\n", p.name, p.multiProcessorCount, freeB / 1048576.0);

    // The production geometry: HC `down`, 10240 -> 320, 3.5 MB per (layer, matrix).
    const int n_in = 10240, n_out = 320;
    const int nblk = n_in / 32;
    const size_t tens = (size_t)n_out * nblk * 34u;      // one copy = one layer's down matrix
    const double one_mib = tens / 1048576.0;

    const int TOTAL_COPIES = 128;                        // fixed total bytes; 851 MiB did not fit
    const size_t bytes = tens * TOTAL_COPIES;
    printf("one copy (layer,matrix) = %.2f MiB   budget = %.0f MiB (%d copies)\n",
           one_mib, bytes / 1048576.0, TOTAL_COPIES);

    unsigned char* w = nullptr;
    if (hipMalloc(&w, bytes) != hipSuccess) { printf("alloc %zu failed\n", bytes); return 1; }
    CHECK(hipMemset(w, 0x5A, bytes));
    float* out = nullptr;
    CHECK(hipMalloc(&out, 1024 * sizeof(float)));
    CHECK(hipMemset(out, 0, 1024 * sizeof(float)));

    const int threads = 64;
    const double total_mib = bytes / 1048576.0;

    printf("\n%-6s %8s %10s %10s %10s\n", "rep", "launches", "ms total", "us/launch", "GB/s");
    printf("-------------------------------------------------------------------\n");

    for (int rep : {1, 2, 4, 8, 16, 32, 64, 128}) {
        const int launches = TOTAL_COPIES / rep;

        // warm up the very first copy so the first timed pass is not a cold TLB/ICache pass
        read_kernel<<<n_out, threads>>>(w, nblk, n_out, tens, 0, 1, out);
        CHECK(hipDeviceSynchronize());

        hipEvent_t a, b;
        CHECK(hipEventCreate(&a)); CHECK(hipEventCreate(&b));
        CHECK(hipEventRecord(a));
        for (int i = 0; i < launches; ++i)
            read_kernel<<<n_out, threads>>>(w, nblk, n_out, tens, i * rep, rep, out);
        CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
        float ms = 0.f; CHECK(hipEventElapsedTime(&ms, a, b));

        printf("%-6d %8d %10.3f %10.2f %10.0f\n",
               rep, launches, ms, ms * 1000.0 / launches,
               total_mib / (ms / 1000.0) / 1024.0);
        CHECK(hipEventDestroy(a)); CHECK(hipEventDestroy(b));
    }

    CHECK(hipFree(out));
    CHECK(hipFree(w));
    printf("\nrep=1 is production's shape (one small kernel per layer); rep=128 is fully batched.\n");
    printf("A rising curve means per-launch cost dominates and the fix is to fuse layers.\n");
    return 0;
}
