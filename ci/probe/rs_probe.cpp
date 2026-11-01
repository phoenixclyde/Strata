// R x S interaction probe on gfx906.
//
// WHY THIS EXISTS
// ---------------
// Everything measured so far moved one knob at a time:
//   * R (rows per block, the native_mmvq "wave rows" table) was swept with S fixed at 1;
//   * S (split-K) was swept with R fixed at 1  (read_probe.cpp, R30).
// Both knobs change parallelism, but along different axes and with opposite effects on locality:
//
//   R up  -> fewer blocks, each walks R complete rows   (output axis merged, more work/block)
//   S up  -> more blocks, each walks 1/S of one row     (reduction axis cut, less work/block)
//
// A row is nblk*34 bytes and rows are far apart in memory, so R changes the *stride pattern*
// while S changes the *length per visit*. If their effects were independent, equal total block
// counts would perform equally. That is exactly what this probe tests: several (R,S) pairs give
// the same block count, and their GB/s are compared directly.
//
// It also answers a practical question for the expert read (R26/R37: production 295 GB/s while
// the same arithmetic in a probe reaches 487). If some (R,S) cell reaches ~500 at the production
// grain, the fix is a launch-geometry change, not a new kernel.
//
// METHOD NOTES (learned the hard way, see read_probe.cpp header)
//   * one launch reads ONE copy of the tensor; the grid's y dimension selects the copy, so no
//     pass can re-read bytes an earlier pass pulled into L2 (that bug once reported 1.5 TB/s,
//     above the 884 GB/s HBM roof);
//   * every block stores a data-dependent reduction, so no load can be optimised away;
//   * the LDS activation tile is filled only for the arithmetic modes, so the pure-read cells
//     are not charged for setup they do not use.
//
// Build: hipcc --offload-arch=gfx906 -O3 -o rs_probe rs_probe.cpp
// Run:   ./rs_probe [quick]

#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>

#define CHECK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    printf("HIP error %s at %s:%d\n", hipGetErrorString(e), __FILE__, __LINE__); exit(1); } } while (0)

// ---- per-block work, identical to the production Q8_0 block layout -------------------------

__device__ inline unsigned int read_block_2b(const unsigned char* p) {
    unsigned int acc = 0u;
    #pragma unroll
    for (int i = 0; i < 17; ++i)
        acc ^= (unsigned int)(*(const unsigned short*)(p + 2 * i));
    return acc;
}

__device__ inline float gemv_block_fma(const unsigned char* p, const float* x) {
    union { unsigned short u; __half h; } cv;
    cv.u = *(const unsigned short*)p;
    const float d = __half2float(cv.h);
    float s = 0.f;
    #pragma unroll
    for (int i = 0; i < 16; ++i) {
        const unsigned short two = *(const unsigned short*)(p + 2 + 2 * i);
        s = fmaf((float)(int)(signed char)(two & 0xFF),      x[2 * i],     s);
        s = fmaf((float)(int)(signed char)((two >> 8) & 0xFF), x[2 * i + 1], s);
    }
    return d * s;
}

__device__ inline float gemv_block_dp4a(const unsigned char* p, const int* xi) {
    union { unsigned short u; __half h; } cv;
    cv.u = *(const unsigned short*)p;
    const float d = __half2float(cv.h);
    int acc = 0;
    #pragma unroll
    for (int i = 0; i < 8; ++i) {
        const int w = (int)(*(const unsigned short*)(p + 2 + 4 * i)) |
                      ((int)(*(const unsigned short*)(p + 4 + 4 * i)) << 16);
        acc = __builtin_amdgcn_sdot4(w, xi[i], acc, false);
    }
    return d * (float)acc;
}

// MODE 0 = pure read, 1 = dequant + FMA, 2 = dequant + dp4a
__global__ void rs_kernel(const unsigned char* __restrict__ w, int nblk, int S, int R, int n_out,
                          size_t copy_stride, int copies, int rep,
                          float* __restrict__ out, int mode) {
    const int gb     = blockIdx.x;
    const int rowgrp = gb / S;          // which group of R rows
    const int sp     = gb % S;          // the split along the reduction axis
    const int lo     = (int)((long long)nblk * sp / S);
    const int hi     = (int)((long long)nblk * (sp + 1) / S);

    const size_t row_bytes = (size_t)nblk * 34u;

    // Activation tile per lane, in REGISTERS. An LDS tile was filled once per block, so its
    // total cost scaled with the block count and made large S look bad for a reason unrelated
    // to arithmetic (S=8 meant 2560 fills of 8 KB against 3.5 MB of data). Registers hold the
    // same 32 values with no fill and no bank structure, isolating the cost of the arithmetic.
    float xr[32];
    int   xi[8];
    if (mode != 0) {
        #pragma unroll
        for (int i = 0; i < 32; ++i) xr[i] = (float)((i + threadIdx.x) & 7) * 0.125f;
        #pragma unroll
        for (int i = 0; i < 8; ++i)  xi[i] = 0x01010101 * ((i + threadIdx.x) & 3);
    }
    // mode 4 keeps the same 32 values in LDS instead, filled ONCE per launch (outside rep):
    // that is production's layout, and the question is what the round trip costs per byte.
    extern __shared__ float xsl[];
    if (mode == 4) {
        for (int i = threadIdx.x; i < 32 * (int)blockDim.x; i += blockDim.x)
            xsl[i] = (float)(i & 7) * 0.125f;
        __syncthreads();
    }

    unsigned int acc = 0u;
    float facc = 0.f;

    // Repeat inside the kernel so launch overhead stops dominating a 3-25 MiB read, and walk a
    // DIFFERENT copy each pass: re-reading the same bytes would hit L2 and report a bandwidth
    // above the HBM roof (that mistake is documented in read_probe.cpp).
    for (int t = 0; t < rep; ++t) {
    const unsigned char* base = w + (size_t)((blockIdx.y + t) % copies) * copy_stride;
    for (int r = 0; r < R; ++r) {
        const unsigned char* rowp = base + (size_t)(rowgrp * R + r) * row_bytes;
        if (mode == 0) {
            for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
                acc ^= read_block_2b(rowp + (size_t)b * 34u);
        } else if (mode == 1) {
            for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
                facc += gemv_block_fma(rowp + (size_t)b * 34u, xr);
        } else if (mode == 2) {
            for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
                facc += gemv_block_dp4a(rowp + (size_t)b * 34u, xi);
        } else if (mode == 4) {
            for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
                facc += gemv_block_fma(rowp + (size_t)b * 34u, xsl + 32 * threadIdx.x);
        } else {
            // mode 3: same arithmetic, ~96 extra live VGPRs. Production's gr_down_q8_kernel
            // uses 119 VGPR at T=2 which is only 25% occupancy on gfx906 (256 VGPR/SIMD,
            // 2 waves). If occupancy is what costs production its 5.6x, this mode drops with it.
            float pad[96];
            #pragma unroll
            for (int i = 0; i < 96; ++i) pad[i] = xr[i & 31] * 0.5f + (float)i;
            for (int b = lo + threadIdx.x; b < hi; b += blockDim.x) {
                facc += gemv_block_fma(rowp + (size_t)b * 34u, xr);
                #pragma unroll
                for (int i = 0; i < 96; i += 8) pad[i] = fmaf(pad[i], 1.0000001f, facc);
            }
            float sink = 0.f;
            #pragma unroll
            for (int i = 0; i < 96; ++i) sink += pad[i];
            facc += sink * 1e-30f;
        }
    }
    }

    acc ^= __float_as_uint(facc);
    __shared__ unsigned int red[256];
    red[threadIdx.x] = acc;
    __syncthreads();
    for (int off = blockDim.x / 2; off > 0; off >>= 1) {
        if (threadIdx.x < off) red[threadIdx.x] ^= red[threadIdx.x + off];
        __syncthreads();
    }
    if (threadIdx.x == 0) out[(blockIdx.x + blockIdx.y) & 1023] = (float)red[0];
}

struct Shape { const char* name; int n_in; int n_out; };

int main(int argc, char** argv) {
    const bool quick = (argc > 1 && argv[1][0] == 'q');

    hipDeviceProp_t p{};
    CHECK(hipGetDeviceProperties(&p, 0));
    size_t freeB = 0, totalB = 0;
    CHECK(hipMemGetInfo(&freeB, &totalB));
    printf("device: %s  CUs=%d  free %.0f MiB\n", p.name, p.multiProcessorCount, freeB / 1048576.0);
    printf("R = rows per block (output axis merged)   S = split-K (reduction axis cut)\n");
    printf("blocks = (n_out/R) * S, so several (R,S) pairs share a block count -- those rows\n");
    printf("are the interaction test: equal parallelism, different locality.\n\n");

    std::vector<Shape> shapes = {
        {"HC down  10240->320 ", 10240, 320},      // the HC bottleneck (R25/R32)
        {"expert    2944k->8  ", 32 * 92206, 8},   // the expert read grain (R26/R37)
        {"GDN qkv  2560->10240",  2560, 10240},    // the biggest dense block
    };

    const int threads = 64;
    float* out = nullptr;
    CHECK(hipMalloc(&out, 1024 * sizeof(float)));
    CHECK(hipMemset(out, 0, 1024 * sizeof(float)));

    const double BUDGET = 360.0 * 1048576.0;
    const int iters = quick ? 1 : 2;
    const int rep   = quick ? 40 : 120;

    printf("%-19s %2s %2s %7s %7s | %6s %6s %6s %6s %6s\n",
           "shape", "R", "S", "blocks", "blk/CU", "read", "fma", "dp4a", "regpr", "lds");
    printf("%s\n", "-------------------------------------------------------------------------------");

    for (auto& sh : shapes) {
        const int nblk = sh.n_in / 32;
        const size_t tens = (size_t)sh.n_out * nblk * 34u;
        int copies = (int)(BUDGET / (double)tens);
        copies = std::max(1, std::min(32, copies));

        unsigned char* w = nullptr;
        if (hipMalloc(&w, tens * copies) != hipSuccess) {
            printf("%-19s alloc failed\n", sh.name); continue;
        }
        CHECK(hipMemset(w, 0x5A, tens * copies));

        const double mib = tens / 1048576.0;
        const double by  = (double)tens * copies;

        for (int R : {1, 2, 4, 8}) {
            if (sh.n_out % R) continue;
            for (int S : {1, 2, 4, 8, 16}) {   // 16 = Q8_NKC, i.e. what production actually uses
                const int blocks = (sh.n_out / R) * S;
                dim3 grid(blocks, copies);

                hipEvent_t a, b;
                CHECK(hipEventCreate(&a)); CHECK(hipEventCreate(&b));
                double gb[5] = {-1, -1, -1, -1, -1};

                for (int mode = 0; mode < 5; ++mode) {
                    // warm
                    const size_t lds = 32 * (size_t)threads * sizeof(float);
                    rs_kernel<<<grid, threads, lds>>>(w, nblk, S, R, sh.n_out, tens, copies, 1, out, mode);
                    CHECK(hipDeviceSynchronize());
                    CHECK(hipEventRecord(a));
                    for (int i = 0; i < iters; ++i)
                        rs_kernel<<<grid, threads, lds>>>(w, nblk, S, R, sh.n_out, tens, copies, rep, out, mode);
                    CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
                    float ms = 0.f; CHECK(hipEventElapsedTime(&ms, a, b));
                    ms /= (float)iters;                 // one launch now carries the rep loop
                    gb[mode] = by * (double)rep / (ms / 1000.0) / 1e9;   // ms -> s
                }
                CHECK(hipEventDestroy(a)); CHECK(hipEventDestroy(b));

                printf("%-19s %2d %2d %7d %7.1f | %6.0f %6.0f %6.0f %6.0f %6.0f\n",
                       (R == 1 && S == 1) ? sh.name : "", R, S, blocks,
                       blocks / (double)p.multiProcessorCount, gb[0], gb[1], gb[2], gb[3], gb[4]);
            }
        }
        printf("\n");
        CHECK(hipFree(w));
    }
    CHECK(hipFree(out));
    printf("read  = pure 17x2B loads        fma = dequant+FMA (tile in registers)\n");
    printf("dp4a  = dequant+v_dot4_i32_i8   regpr = fma + 96 dummy VGPRs (production-like occupancy)\n");
    printf("lds   = fma with the activation tile in LDS (production's layout), filled once per launch\n");
    printf("Compare ROWS WITH THE SAME block count to see whether R and S are interchangeable.\n");
    return 0;
}
