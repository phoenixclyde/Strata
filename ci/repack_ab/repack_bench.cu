// W999: minimal single-kernel A/B harness for mx repacked Q5_1 MoE GEMM.
// Numbers are meaningless (random weights/activations); only kernel time matters.
#include "repack/repack-kernels.cuh"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <random>
#include <hip/hip_runtime.h>

#define CK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    std::fprintf(stderr, "HIP %s:%d: %s\n", __FILE__, __LINE__, hipGetErrorString(e)); std::exit(1); } } while (0)

template <typename T> struct D {
    T * p = nullptr;
    explicit D(size_t bytes) { CK(hipMalloc(&p, bytes)); }
    ~D() { if (p) hipFree(p); }
};

// verbatim host logic from mx/repack-common.cu:285 (planes are copies for Q5_1)
static void repack_q51(const block_q5_1 * blocks, uint8_t * dst, int64_t ne0, int64_t ne1) {
    const int64_t n_sub  = ne0 / 32;
    const int64_t qs_str = repack_qs_row_stride(GGML_TYPE_Q5_1, ne0);
    const size_t  hoff   = (size_t) ne1 * qs_str;
    const size_t  doff   = hoff + (size_t) ne1 * n_sub * 4;
    std::memset(dst, 0, doff + (size_t) ne1 * n_sub * 4);
    for (int64_t row = 0; row < ne1; row++) {
        const block_q5_1 * brow = blocks + row * n_sub;
        for (int64_t sb = 0; sb < n_sub; sb++) {
            const block_q5_1 * b = &brow[sb];
            const size_t wi = (size_t) row * n_sub + sb;
            std::memcpy(dst + (size_t) row * qs_str + (size_t) sb * 16, b->qs, 16);
            std::memcpy(dst + hoff + wi * 4, b->qh, 4);
            std::memcpy(dst + doff + wi * 4, &b->dm, 4);
        }
    }
}

int main(int argc, char ** argv) {
    const int n          = argc > 1 ? std::atoi(argv[1]) : 16;
    const int rows_per   = argc > 2 ? std::atoi(argv[2]) : 320;
    const int reps       = argc > 3 ? std::atoi(argv[3]) : 10;
    const int out_rows   = 640;
    const int cols       = 2560;
    const int rows       = n * rows_per;
    const int n_sub      = cols / 32;

    // ---- canonical Q5_1 weights (random bytes) ----
    const size_t canon_bytes = (size_t) out_rows * n_sub * sizeof(block_q5_1);
    const size_t stride      = repack_gcn_nbytes(GGML_TYPE_Q5_1, cols, out_rows);
    std::printf("shape: experts=%d rows/expert=%d out_rows=%d cols=%d canon=%zu repack_stride=%zu\n",
                n, rows_per, out_rows, cols, canon_bytes, stride);

    std::mt19937 rng(999);
    std::vector<uint8_t> canon((size_t) n * canon_bytes);
    for (auto & b : canon) b = (uint8_t) (rng() & 0xff);
    std::vector<uint8_t> rep((size_t) n * stride, 0);
    for (int e = 0; e < n; ++e) {
        repack_q51((const block_q5_1 *) (canon.data() + (size_t) e * canon_bytes),
                        rep.data() + (size_t) e * stride, cols, out_rows);
    }

    // mx GEMM consumes the GROUPED MMQ activation layout: block_q8_1_mmq = 128 values + 16 B header
    // (sizeof == 4*sizeof(block_q8_1)), NOT a linear array of stock 32-value block_q8_1.
    // Zero content is fine for timing; the size/stride must match the kernel's indexing.
    constexpr int VPM = 4 * QK8_1;   // 128 values per grouped block
    const size_t nblk = (size_t) (cols / VPM);
    const size_t xq_bytes = (size_t) rows * nblk * sizeof(block_q8_1_mmq) * 2;
    std::vector<uint8_t> xq(xq_bytes, 0);

    // ---- bounds / ids / tile metadata ----
    std::vector<int32_t> bounds(n + 1, 0), ids(rows);
    for (int e = 0; e < n; ++e) bounds[e + 1] = bounds[e] + rows_per;
    for (int i = 0; i < rows; ++i) ids[i] = i;
    constexpr int BN_ID  = 64 * MMQ_RP_Q8_TN;   // 128, 64-wide GEMM
    constexpr int BN_W32 = 32 * 1;              // 32,  w32 GEMM
    const bool use_w32 = rows < 2 * BN_ID * n;  // verbatim mx mul-mat-id.cu:216
    const int BN = use_w32 ? BN_W32 : BN_ID;
    const int max_tiles = rows / BN + n + 4;
    std::vector<repack_tile_meta> meta(max_tiles);
    std::vector<int32_t> tile_off(n + 1, 0);
    int acc = 0;
    for (int e = 0; e < n; ++e) {
        const int cnt = bounds[e + 1] - bounds[e];
        const int nt = (cnt + BN - 1) / BN;
        for (int t = 0; t < nt && acc + t < max_tiles; ++t) {
            meta[acc + t].expert = (uint32_t) e;
            meta[acc + t].a_base = (uint32_t) bounds[e] + (uint32_t) t * BN;
        }
        acc += nt;
        tile_off[e + 1] = acc;
    }

    D<uint8_t> dw(rep.size()), dxq(xq_bytes), dy((size_t) rows * out_rows * sizeof(float));
    D<int32_t> db((n + 1) * sizeof(int32_t)), did((size_t) rows * sizeof(int32_t)),
               dto((n + 1) * sizeof(int32_t));
    D<repack_tile_meta> dm(sizeof(repack_tile_meta) * max_tiles);
    CK(hipMemcpy(dw.p, rep.data(), rep.size(), hipMemcpyHostToDevice));
    CK(hipMemcpy(dxq.p, xq.data(), xq_bytes, hipMemcpyHostToDevice));
    CK(hipMemcpy(db.p, bounds.data(), db.p ? (n + 1) * sizeof(int32_t) : 0, hipMemcpyHostToDevice));
    CK(hipMemcpy(did.p, ids.data(), (size_t) rows * sizeof(int32_t), hipMemcpyHostToDevice));
    CK(hipMemcpy(dto.p, tile_off.data(), (n + 1) * sizeof(int32_t), hipMemcpyHostToDevice));
    CK(hipMemcpy(dm.p, meta.data(), sizeof(repack_tile_meta) * max_tiles, hipMemcpyHostToDevice));

    hipStream_t s; CK(hipStreamCreateWithFlags(&s, hipStreamNonBlocking));
    const dim3 grid((out_rows + MMQ_RP_Q8_BM - 1) / MMQ_RP_Q8_BM, max_tiles, 1);
    const dim3 block(use_w32 ? 32 : 64,
                     use_w32 ? MMQ_RP_Q8_NROW_LANES * 2 : MMQ_RP_Q8_NROW_LANES);
    std::printf("dispatch: %s BN=%d grid=(%d,%d) block=(%d,%d) tiles=%d xq_bytes=%zu\n",
                use_w32 ? "w32" : "w64", BN, grid.x, grid.y, block.x, block.y, acc, xq_bytes);

#define RP_ARGS dw.p, (const block_q8_1 *) dxq.p, (float *) dy.p, \
                (uint32_t) cols, (uint32_t) out_rows, (uint32_t) rows, \
                did.p, did.p, db.p, dto.p, dm.p, \
                (uint32_t) n, stride, (uint32_t) out_rows

    auto launch = [&]() {
        if (use_w32) {
            mmq_gemm_repacked_w32<true, 1, MMQ_RP_Q8_NROW_LANES * 2, GGML_TYPE_Q5_1>
                <<<grid, block, 0, s>>>(RP_ARGS);
        } else {
            mmq_gemm_repacked<true, MMQ_RP_Q8_TN, MMQ_RP_Q8_NROW_LANES, GGML_TYPE_Q5_1>
                <<<grid, block, 0, s>>>(RP_ARGS);
        }
    };
#undef RP_ARGS
    launch(); CK(hipStreamSynchronize(s));   // warm-up
    hipError_t e = hipGetLastError();
    if (e != hipSuccess) { std::fprintf(stderr, "launch: %s\n", hipGetErrorString(e)); return 2; }

    for (int r = 0; r < reps; ++r) {
        hipEvent_t a, b; CK(hipEventCreate(&a)); CK(hipEventCreate(&b));
        CK(hipEventRecord(a, s)); launch(); CK(hipEventRecord(b, s));
        CK(hipStreamSynchronize(s));
        float ms = 0; CK(hipEventElapsedTime(&ms, a, b));
        double mac = (double) rows * out_rows * cols;
        std::printf("rep %d: %.3f ms  %.2f TMAC/s\n", r + 1, ms, mac / (ms * 1e9));
        CK(hipEventDestroy(a)); CK(hipEventDestroy(b));
    }
    CK(hipStreamDestroy(s));
    std::printf("repacked bench done\n");
    return 0;
}
