// STREAM-style bandwidth roof for gfx906 / MI50 32GB.
//
// Why: every "% of peak" number in the W863 plan used a denominator of ~700 GB/s that was
// never measured (98 GB/s / 0.14 = 700). The AMD spec is 1024 GB/s (4096-bit HBM2 @ 1 GHz),
// but a spec is not a roof -- GPU-STREAM and the roofline literature both say a STREAM-class
// kernel reaches ~80% of spec, and ECC costs more on top. Measuring beats assuming, so this
// probe reports the achievable read roof and the achievable copy roof on this exact card,
// with the exact allocation sizes that fit next to a resident 33.5 GiB model.
//
// Read roof is the one that matters for decode: a decode step reads weights and writes almost
// nothing, so read-only bandwidth is the physical ceiling for tokens/s.
//
// Build: hipcc --offload-arch=gfx906 -O3 -o stream_roof stream_roof.cpp
// Run:   ./stream_roof [maxMiB] [iterations]

#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>

#define CHECK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    printf("HIP error %s at %s:%d\n", hipGetErrorString(e), __FILE__, __LINE__); exit(1); } } while (0)

// Read-only, grid-stride, 16 B per thread per step (uint4 = one 16 B transaction per lane).
__global__ void read_kernel(const uint4* __restrict__ src, unsigned long long n4, float* out) {
    unsigned long long i = (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
    const unsigned long long stride = (unsigned long long)gridDim.x * blockDim.x;
    uint4 acc = make_uint4(0u, 0u, 0u, 0u);
    for (; i < n4; i += stride) {
        uint4 v = src[i];
        acc.x ^= v.x; acc.y ^= v.y; acc.z ^= v.z; acc.w ^= v.w;
    }
    unsigned int r = acc.x ^ acc.y ^ acc.z ^ acc.w;
    if (r == 0xFFFFFFFFu) out[0] = (float)r;   // unreachable; keeps the loads alive
}

// Copy: read + write, the classic STREAM shape, for a second reference point.
__global__ void copy_kernel(const uint4* __restrict__ src, uint4* __restrict__ dst,
                            unsigned long long n4) {
    unsigned long long i = (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
    const unsigned long long stride = (unsigned long long)gridDim.x * blockDim.x;
    for (; i < n4; i += stride) dst[i] = src[i];
}

struct Result { double gbs; };

static Result run_read(const uint4* buf, unsigned long long n4, float* out,
                       int blocks, int threads, int iters) {
    hipEvent_t a, b;
    CHECK(hipEventCreate(&a)); CHECK(hipEventCreate(&b));
    read_kernel<<<blocks, threads>>>(buf, n4, out);              // warm up
    CHECK(hipDeviceSynchronize());
    CHECK(hipEventRecord(a));
    for (int i = 0; i < iters; ++i) read_kernel<<<blocks, threads>>>(buf, n4, out);
    CHECK(hipEventRecord(b));
    CHECK(hipEventSynchronize(b));
    float ms = 0.f; CHECK(hipEventElapsedTime(&ms, a, b));
    CHECK(hipEventDestroy(a)); CHECK(hipEventDestroy(b));
    double bytes = (double)n4 * 16.0 * (double)iters;
    return Result{bytes / (ms / 1000.0) / 1e9};
}

static Result run_copy(const uint4* src, uint4* dst, unsigned long long n4,
                       int blocks, int threads, int iters) {
    hipEvent_t a, b;
    CHECK(hipEventCreate(&a)); CHECK(hipEventCreate(&b));
    copy_kernel<<<blocks, threads>>>(src, dst, n4);
    CHECK(hipDeviceSynchronize());
    CHECK(hipEventRecord(a));
    for (int i = 0; i < iters; ++i) copy_kernel<<<blocks, threads>>>(src, dst, n4);
    CHECK(hipEventRecord(b));
    CHECK(hipEventSynchronize(b));
    float ms = 0.f; CHECK(hipEventElapsedTime(&ms, a, b));
    CHECK(hipEventDestroy(a)); CHECK(hipEventDestroy(b));
    double bytes = (double)n4 * 16.0 * 2.0 * (double)iters;   // read + write
    return Result{bytes / (ms / 1000.0) / 1e9};
}

int main(int argc, char** argv) {
    int max_mib = argc > 1 ? atoi(argv[1]) : 384;
    int iters   = argc > 2 ? atoi(argv[2]) : 20;

    hipDeviceProp_t p{};
    CHECK(hipGetDeviceProperties(&p, 0));
    printf("device: %s  arch=%s  CUs=%d  warpSize=%d  clock=%d kHz\n",
           p.name, p.gcnArchName, p.multiProcessorCount, p.warpSize, p.clockRate);
    size_t freeB = 0, totalB = 0;
    CHECK(hipMemGetInfo(&freeB, &totalB));
    printf("vram: free %.0f MiB / total %.0f MiB\n\n", freeB / 1048576.0, totalB / 1048576.0);

    std::vector<int> sizes;
    for (int m = 32; m <= max_mib; m *= 2) sizes.push_back(m);

    const int threads = 256;
    std::vector<int> mults = {1, 2, 4, 8, 16, 32};

    printf("=== read roof (16 B per lane per step, grid-stride) ===\n");
    printf("%6s %8s %10s %10s\n", "MiB", "blocks", "GB/s", "%of1024");

    double best_read = 0.0; int best_mib = 0, best_blocks = 0;
    for (int mib : sizes) {
        size_t bytes = (size_t)mib << 20;
        void* buf = nullptr;
        if (hipMalloc(&buf, bytes) != hipSuccess) { printf("%6d  (alloc failed, skipped)\n", mib); continue; }
        // fill so the pages are really resident
        CHECK(hipMemset(buf, 0x5A, bytes));
        float* out = nullptr; CHECK(hipMalloc(&out, 4)); CHECK(hipMemset(out, 0, 4));
        unsigned long long n4 = bytes / 16;
        for (int mult : mults) {
            int blocks = p.multiProcessorCount * mult;
            Result r = run_read((const uint4*)buf, n4, out, blocks, threads, iters);
            if (r.gbs > best_read) { best_read = r.gbs; best_mib = mib; best_blocks = blocks; }
            printf("%6d %8d %10.1f %9.1f%%\n", mib, blocks, r.gbs, 100.0 * r.gbs / 1024.0);
        }
        CHECK(hipFree(out));
        CHECK(hipFree(buf));
    }

    printf("\n=== copy roof (read+write counts both directions) ===\n");
    printf("%6s %8s %10s\n", "MiB", "blocks", "GB/s");
    double best_copy = 0.0;
    for (int mib : sizes) {
        if (mib > max_mib / 2) continue;                 // needs twice the footprint
        size_t bytes = (size_t)mib << 20;
        void* a = nullptr; void* b = nullptr;
        if (hipMalloc(&a, bytes) != hipSuccess || hipMalloc(&b, bytes) != hipSuccess) {
            printf("%6d  (alloc failed, skipped)\n", mib); continue;
        }
        CHECK(hipMemset(a, 0x5A, bytes)); CHECK(hipMemset(b, 0, bytes));
        unsigned long long n4 = bytes / 16;
        for (int mult : {8, 16, 32}) {
            int blocks = p.multiProcessorCount * mult;
            Result r = run_copy((const uint4*)a, (uint4*)b, n4, blocks, threads, iters);
            best_copy = std::max(best_copy, r.gbs);
            printf("%6d %8d %10.1f\n", mib, blocks, r.gbs);
        }
        CHECK(hipFree(a)); CHECK(hipFree(b));
    }

    printf("\n=== verdict ===\n");
    printf("best read roof = %.1f GB/s  (%d MiB, %d blocks) = %.1f%% of the 1024 GB/s spec\n",
           best_read, best_mib, best_blocks, 100.0 * best_read / 1024.0);
    printf("best copy roof = %.1f GB/s\n", best_copy);
    printf("use READ as the decode roof: a decode step writes ~nothing.\n");
    return 0;
}
