// Controlled read probe for the HC (hyper-connection) tensor geometry on gfx906.
//
// Two questions the plan could not answer with existing data:
//
//   Q1 (R30) Does more parallelism help a decode-style read? The literature says yes for skinny
//           GEMV -- split-K fills the machine when the output axis is short -- while our earlier
//           data said "fewer blocks is faster". That earlier experiment changed block count AND
//           rows-per-block together. Here only the block count changes: the same bytes are split
//           S ways along the reduction axis and nothing else moves.
//
//   Q2 (R28/R31) What does the 2-byte load pattern cost? A Q8_0 block is 34 bytes, so block starts
//           are only 2-byte aligned and a 32-bit load is misaligned half the time. The real kernel
//           therefore issues scalar loads. A tile could still be streamed with 16-byte loads and
//           deinterleaved in LDS afterwards, so:
//
//             mode 0  structure-respecting: 17 x 2-byte loads per 34-byte block (today's pattern)
//             mode 1  streaming ceiling:    16-byte loads over the same bytes, block structure ignored
//
//   mode 1 is an upper bound for "what if LDS staging worked", not a drop-in kernel.
//
// Measurement design (this is where two earlier versions of this file went wrong):
//   * one launch reads ONE copy of the tensor; `copies` copies are allocated up front and the grid's
//     y dimension selects the copy, so no pass re-reads bytes an earlier pass pulled into L2
//     (that mistake reported 1.5 TB/s -- above the 884 GB/s HBM roof -- because the re-reads were
//     cache hits);
//   * every block stores its own reduction to a data-dependent place, so no load feeding it can be
//     optimised away (an `if (result == impossible)` guard was, along with the loads).
//
// Build: hipcc --offload-arch=gfx906 -O3 -o read_probe read_probe.cpp
// Run:   ./read_probe

#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>

#define CHECK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    printf("HIP error %s at %s:%d\n", hipGetErrorString(e), __FILE__, __LINE__); exit(1); } } while (0)

__device__ inline unsigned int read_block_2b(const unsigned char* p) {
    unsigned int acc = 0u;
    #pragma unroll
    for (int i = 0; i < 17; ++i)                      // 1 fp16 scale + 32 int8 taken as 16 pairs
        acc ^= (unsigned int)(*(const unsigned short*)(p + 2 * i));
    return acc;
}

// mode 2: the same loads, then the arithmetic the HC down kernel actually does on them --
// dequantise 32 int8 with the fp16 scale and accumulate against an activation vector held in LDS.
// This isolates "the bytes cost X" from "the work per byte costs Y".
__device__ inline float gemv_block_dp4a(const unsigned char* p, const int* xi) {
    union { unsigned short u; __half h; } cv;
    cv.u = *(const unsigned short*)p;
    const float d = __half2float(cv.h);
    int acc = 0;
    #pragma unroll
    for (int i = 0; i < 8; ++i) {
        // 4 int8 weights per 32-bit word, exactly how the production kernel already packs q[r][s]
        const int w = (int)(*(const unsigned short*)(p + 2 + 4 * i)) |
                      ((int)(*(const unsigned short*)(p + 4 + 4 * i)) << 16);
        acc = __builtin_amdgcn_sdot4(w, xi[i], acc, false);
    }
    return d * (float) acc;
}

__device__ inline float gemv_block(const unsigned char* p, const float* x) {
    union { unsigned short u; __half h; } cv;
    cv.u = *(const unsigned short*)p;
    const float d = __half2float(cv.h);
    float s = 0.f;
    #pragma unroll
    for (int i = 0; i < 16; ++i) {
        const unsigned short two = *(const unsigned short*)(p + 2 + 2 * i);
        const int q0 = (int)(signed char)(two & 0xFF);
        const int q1 = (int)(signed char)(two >> 8);
        s = fmaf((float) q0, x[2 * i], s);
        s = fmaf((float) q1, x[2 * i + 1], s);
    }
    return d * s;
}

__global__ void probe(const unsigned char* __restrict__ w, int nblk, int S, int n_out,
                      size_t copy_stride, float* __restrict__ out, int mode) {
    const int gb  = blockIdx.x;
    const int row = gb / S;
    const int sp  = gb % S;
    const int lo  = (int)((long long)nblk * sp / S);
    const int hi  = (int)((long long)nblk * (sp + 1) / S);

    const size_t row_bytes = (size_t)nblk * 34u;
    const unsigned char* rowp = w + (size_t)blockIdx.y * copy_stride + (size_t)row * row_bytes;

    // activation tile in LDS, as the real kernel keeps it: 32 floats per lane.
    // Only filled for the gemv mode -- filling it unconditionally charged every mode for the
    // setup and moved the baselines (measured: GDN read fell 566 -> 238 GB/s for that reason alone).
    extern __shared__ float xs[];
    if (mode == 2 || mode == 3) {
        const int per = (mode == 3) ? 33 : 32;
        for (int i = threadIdx.x; i < per * (int)blockDim.x; i += blockDim.x)
            xs[i] = (float) (i & 7) * 0.125f;
    }
    int* xi = reinterpret_cast<int*>(xs);          // mode 4 reads the same tile as 8 int8 words
    if (mode == 4)
        for (int i = threadIdx.x; i < 32 * (int)blockDim.x; i += blockDim.x)
            xi[i] = 0x01010101 * (i & 3);

    unsigned int acc = 0u;
    float facc = 0.f;
    if (mode == 0) {
        for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
            acc ^= read_block_2b(rowp + (size_t)b * 34u);
    } else if (mode == 2) {
        for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
            facc += gemv_block(rowp + (size_t)b * 34u, xs + 32 * threadIdx.x);
    } else if (mode == 3) {
        for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
            facc += gemv_block(rowp + (size_t)b * 34u, xs + 33 * threadIdx.x);
    } else if (mode == 4) {
        for (int b = lo + threadIdx.x; b < hi; b += blockDim.x)
            facc += gemv_block_dp4a(rowp + (size_t)b * 34u, xi + 8 * threadIdx.x);
    } else {
        const int n16   = (int)(row_bytes / 16u);
        const int lo16  = (int)((long long)n16 * sp / S);
        const int hi16  = (int)((long long)n16 * (sp + 1) / S);
        const uint4* v  = (const uint4*)rowp;
        for (int i = lo16 + threadIdx.x; i < hi16; i += blockDim.x) {
            uint4 t = v[i];
            acc ^= t.x ^ t.y ^ t.z ^ t.w;
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
    if (threadIdx.x == 0) out[gb & 1023] = (float)red[0];
}

struct Shape { const char* name; int n_in; int n_out; };

int main() {
    hipDeviceProp_t p{};
    CHECK(hipGetDeviceProperties(&p, 0));
    size_t freeB = 0, totalB = 0;
    CHECK(hipMemGetInfo(&freeB, &totalB));
    printf("device: %s  CUs=%d  warpSize=%d  free %.0f MiB\n\n",
           p.name, p.multiProcessorCount, p.warpSize, freeB / 1048576.0);

    std::vector<Shape> shapes = {
        {"HC down  10240->320 ", 10240, 320},
        {"HC up     320->10240",   320, 10240},
        {"GDN qkv  2560->10240",  2560, 10240},
        {"big     10240->8192 ", 10240, 8192},   // 85 MiB: far past the 4 MB L2
        // The expert block: 3.13 MB per (layer, expert) slot, read as 8 of them (25 MB, one
        // tensor's worth of a layer). Used to ask whether a 3.13 MB gather is a streaming read
        // or something the kernel turns into a latency problem.
        {"expert 3.13MB x8 ", 32 * 92206, 8},
    };
    const int threads = 64;

    float* out = nullptr;
    CHECK(hipMalloc(&out, 1024 * sizeof(float))); CHECK(hipMemset(out, 0, 1024 * sizeof(float)));

    printf("%-20s %3s %7s %8s %6s %6s %6s %6s %6s | %5s %5s %5s %5s %5s\n",
           "shape", "S", "blocks", "MiB", "read", "wide", "gemv", "pad", "dp4a", "rd", "wide", "gemv", "pad", "dp4a");
    printf("%s\n", "-------------------------------------------------------------------------------------------------------");

    const double BUDGET = 360.0 * 1048576.0;   // keep the probe under 360 MiB next to production

    for (auto& sh : shapes) {
        const int nblk = sh.n_in / 32;
        const size_t tens = (size_t)sh.n_out * nblk * 34u;
        int copies = (int)(BUDGET / (double)tens);
        copies = std::max(1, std::min(64, copies));
        const size_t bytes = tens * copies;

        unsigned char* w = nullptr;
        if (hipMalloc(&w, bytes) != hipSuccess) { printf("%-22s alloc %zu B failed\n", sh.name, bytes); continue; }
        CHECK(hipMemset(w, 0x5A, bytes));

        const bool can16 = (tens / sh.n_out) % 16u == 0u;
        const double mib = tens / 1048576.0;
        if (!can16)
            printf("%-22s row %zu B not a multiple of 16 -> mode1 skipped\n", sh.name, tens / sh.n_out);

        for (int S : {1, 2, 4, 8, 16}) {
            const int blocks = sh.n_out * S;
            dim3 grid(blocks, copies);

            const size_t lds = 33 * (size_t)threads * sizeof(float);   // padded: 33 floats per lane
            probe<<<grid, threads>>>(w, nblk, S, sh.n_out, tens, out, 0);
            if (can16) probe<<<grid, threads>>>(w, nblk, S, sh.n_out, tens, out, 1);
            probe<<<grid, threads, lds>>>(w, nblk, S, sh.n_out, tens, out, 2);
            CHECK(hipDeviceSynchronize());

            hipEvent_t a, b;
            CHECK(hipEventCreate(&a)); CHECK(hipEventCreate(&b));

            CHECK(hipEventRecord(a));
            probe<<<grid, threads>>>(w, nblk, S, sh.n_out, tens, out, 0);
            CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
            float ms0 = 0.f; CHECK(hipEventElapsedTime(&ms0, a, b));

            float ms1 = -1.f;
            if (can16) {
                CHECK(hipEventRecord(a));
                probe<<<grid, threads>>>(w, nblk, S, sh.n_out, tens, out, 1);
                CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
                CHECK(hipEventElapsedTime(&ms1, a, b));
            }
            CHECK(hipEventRecord(a));
            probe<<<grid, threads, lds>>>(w, nblk, S, sh.n_out, tens, out, 2);
            CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
            float ms2 = 0.f; CHECK(hipEventElapsedTime(&ms2, a, b));

            CHECK(hipEventRecord(a));
            probe<<<grid, threads, lds>>>(w, nblk, S, sh.n_out, tens, out, 3);
            CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
            float ms3 = 0.f; CHECK(hipEventElapsedTime(&ms3, a, b));

            CHECK(hipEventRecord(a));
            probe<<<grid, threads, lds>>>(w, nblk, S, sh.n_out, tens, out, 4);
            CHECK(hipEventRecord(b)); CHECK(hipEventSynchronize(b));
            float ms4 = 0.f; CHECK(hipEventElapsedTime(&ms4, a, b));

            CHECK(hipEventDestroy(a)); CHECK(hipEventDestroy(b));

            const double by = copies * mib * 1048576.0;
            const double gb0 = by / (ms0 / 1000.0) / 1e9;
            const double gb2 = by / (ms2 / 1000.0) / 1e9;
            if (can16) {
                const double gb1 = by / (ms1 / 1000.0) / 1e9;
                const double gb3 = by / (ms3 / 1000.0) / 1e9;
                const double gb4 = by / (ms4 / 1000.0) / 1e9;
                printf("%-20s %3d %7d %8.2f %8.2f %8.2f %8.2f %8.2f %8.2f | %5.0f %5.0f %5.0f %5.0f %5.0f\n",
                       S == 1 ? sh.name : "", S, blocks, mib, ms0, ms1, ms2, ms3, ms4,
                       gb0, gb1, gb2, gb3, gb4);
            } else {
                const double gb3 = by / (ms3 / 1000.0) / 1e9;
                printf("%-20s %3d %7d %8.2f %8.2f %8s %8.2f %8.2f | %5.0f %5s %5.0f %5.0f\n",
                       S == 1 ? sh.name : "", S, blocks, mib, ms0, "n/a", ms2, ms3, gb0, "-", gb2, gb3);
            }
        }
        CHECK(hipFree(w));
        printf("\n");
    }
    CHECK(hipFree(out));

    printf("copies chosen so the whole buffer stays under 360 MiB; each grid.y slice is a distinct\n");
    printf("copy, so no pass can hit cache lines an earlier pass brought in.\n");
    printf("mode0 = 17 x 2-byte loads per 34-byte Q8_0 block (what the HC kernel does today)\n");
    printf("mode1 = 16-byte streaming loads over the same bytes (ceiling if LDS staging works)\n");
    printf("S     = split-K factor: same bytes, S times as many blocks\n");
    printf("gemv  = mode 2: the same 2-byte loads + dequant + FMA against an LDS activation tile\n");
    return 0;
}
