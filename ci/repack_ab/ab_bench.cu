// W1001: FAIR A/B for mx repacked Q5_1 MoE GEMM.
// Both arms consume the SAME activation buffer produced by our own mmq::quantize
// (grouped MMQ layout), so only the weight layout / kernel differ.
#include "repack/repack-kernels.cuh"
#include "strata/prefill/moe_mmq.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <random>
#include <hip/hip_runtime.h>

namespace mmq = strata::prefill::mmq;

#define CK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    std::fprintf(stderr, "HIP %s:%d: %s\n", __FILE__, __LINE__, hipGetErrorString(e)); std::exit(1); } } while (0)

template <typename T> struct D {
    T * p = nullptr;
    explicit D(size_t bytes) { CK(hipMalloc(&p, bytes)); }
    ~D() { if (p) hipFree(p); }
};

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
    const int n        = argc > 1 ? std::atoi(argv[1]) : 16;
    const int rows_per = argc > 2 ? std::atoi(argv[2]) : 320;
    const int reps     = argc > 3 ? std::atoi(argv[3]) : 5;
    const int out_rows = 640, cols = 2560;
    const int rows = n * rows_per;
    const int n_sub = cols / 32;

    const size_t eb     = mmq::matrix_bytes(7, out_rows, cols);
    const size_t stride = repack_gcn_nbytes(GGML_TYPE_Q5_1, cols, out_rows);
    const size_t xq_sz  = mmq::q8_bytes(rows, cols) * 2;
    std::printf("shape: experts=%d rows/expert=%d w=[%d,%d] eb=%zu repack_stride=%zu xq=%zu\n",
                n, rows_per, out_rows, cols, eb, stride, xq_sz);

    std::mt19937 rng(1001);
    std::vector<uint8_t> w((size_t) n * eb + 4096);
    for (auto & b : w) b = (uint8_t) (rng() & 0xff);
    std::vector<float> x((size_t) rows * cols);
    for (auto & v : x) v = (float) ((rng() % 2000) - 1000) / 1000.0f;
    std::vector<int32_t> bounds(n + 1, 0), ids(rows);
    for (int e = 0; e < n; ++e) bounds[e + 1] = bounds[e] + rows_per;
    for (int i = 0; i < rows; ++i) ids[i] = i;

    std::vector<uint8_t> rep((size_t) n * stride, 0);
    for (int e = 0; e < n; ++e)
        repack_q51((const block_q5_1 *) (w.data() + (size_t) e * eb),
                   rep.data() + (size_t) e * stride, cols, out_rows);

    constexpr int BN_ID = 64 * MMQ_RP_Q8_TN, BN_W32 = 32 * 1;
    const bool use_w32 = rows < 2 * BN_ID * n;
    const int BN = use_w32 ? BN_W32 : BN_ID;
    const int max_tiles = rows / BN + n + 4;
    std::vector<repack_tile_meta> meta(max_tiles);
    std::vector<int32_t> tile_off(n + 1, 0);
    int acc = 0;
    for (int e = 0; e < n; ++e) {
        const int cnt = bounds[e + 1] - bounds[e], nt = (cnt + BN - 1) / BN;
        for (int t = 0; t < nt && acc + t < max_tiles; ++t) {
            meta[acc + t].expert = (uint32_t) e;
            meta[acc + t].a_base = (uint32_t) bounds[e] + (uint32_t) t * BN;
        }
        acc += nt; tile_off[e + 1] = acc;
    }

    D<uint8_t> dw(w.size()), dwr(rep.size()), dx(x.size() * 4), dxq(xq_sz),
               dy((size_t) rows * out_rows * 4);
    D<int32_t> db((n + 1) * 4), did((size_t) rows * 4), dto((n + 1) * 4);
    D<repack_tile_meta> dm(sizeof(repack_tile_meta) * max_tiles);
    CK(hipMemcpy(dw.p,  w.data(),   w.size(),   hipMemcpyHostToDevice));
    CK(hipMemcpy(dwr.p, rep.data(), rep.size(), hipMemcpyHostToDevice));
    CK(hipMemcpy(dx.p,  x.data(),   x.size()*4, hipMemcpyHostToDevice));
    CK(hipMemcpy(db.p,  bounds.data(),  (n+1)*4, hipMemcpyHostToDevice));
    CK(hipMemcpy(did.p, ids.data(), (size_t) rows*4, hipMemcpyHostToDevice));
    CK(hipMemcpy(dto.p, tile_off.data(), (n+1)*4, hipMemcpyHostToDevice));
    CK(hipMemcpy(dm.p,  meta.data(), sizeof(repack_tile_meta)*max_tiles, hipMemcpyHostToDevice));

    hipStream_t s; CK(hipStreamCreateWithFlags(&s, hipStreamNonBlocking));
    // SAME activation buffer for both arms
    mmq::quantize((const float *) dx.p, did.p, dxq.p, 7, cols, cols, rows, s);
    CK(hipStreamSynchronize(s));

    mmq::Product p;
    p.w = dw.p; p.type = 7; p.w_rows = out_rows; p.w_cols = cols; p.expert_bytes = eb; p.n = n;
    p.xq = dxq.p; p.bounds = db.p; p.ids = did.p;
    p.total_rows = rows; p.max_rows = rows_per; p.dst = (float *) dy.p; p.ld_dst = out_rows;
    mmq::Context ctx;

    const dim3 grid((out_rows + MMQ_RP_Q8_BM - 1) / MMQ_RP_Q8_BM, max_tiles, 1);
    const dim3 block(use_w32 ? 32 : 64, use_w32 ? MMQ_RP_Q8_NROW_LANES*2 : MMQ_RP_Q8_NROW_LANES);
    std::printf("dispatch: %s BN=%d grid=(%d,%d) block=(%d,%d) tiles=%d\n",
                use_w32 ? "w32" : "w64", BN, grid.x, grid.y, block.x, block.y, acc);

#define RP_ARGS dwr.p, (const block_q8_1 *) dxq.p, (float *) dy.p, \
                (uint32_t) cols, (uint32_t) out_rows, (uint32_t) rows, \
                did.p, did.p, db.p, dto.p, dm.p, (uint32_t) n, stride, (uint32_t) out_rows
    auto launch_rep = [&]() {
        if (use_w32)
            mmq_gemm_repacked_w32<true, 1, MMQ_RP_Q8_NROW_LANES*2, GGML_TYPE_Q5_1><<<grid, block, 0, s>>>(RP_ARGS);
        else
            mmq_gemm_repacked<true, MMQ_RP_Q8_TN, MMQ_RP_Q8_NROW_LANES, GGML_TYPE_Q5_1><<<grid, block, 0, s>>>(RP_ARGS);
    };
#undef RP_ARGS
    auto launch_can = [&]() { ctx.run(p, s); };

    launch_can(); launch_rep(); CK(hipStreamSynchronize(s));   // warm-up both
    hipError_t e = hipGetLastError();
    if (e != hipSuccess) { std::fprintf(stderr, "launch: %s\n", hipGetErrorString(e)); return 2; }

    std::vector<double> tc, tr;
    for (int r = 0; r < reps; ++r) {
        hipEvent_t a, b, c, d;
        CK(hipEventCreate(&a)); CK(hipEventCreate(&b)); CK(hipEventCreate(&c)); CK(hipEventCreate(&d));
        CK(hipEventRecord(a, s)); launch_can(); CK(hipEventRecord(b, s));
        CK(hipEventRecord(c, s)); launch_rep(); CK(hipEventRecord(d, s));
        CK(hipStreamSynchronize(s));
        float mc = 0, mr = 0;
        CK(hipEventElapsedTime(&mc, a, b)); CK(hipEventElapsedTime(&mr, c, d));
        tc.push_back(mc); tr.push_back(mr);
        std::printf("rep %d: canonical %.3f ms | repacked %.3f ms | ratio %.3f\n", r+1, mc, mr, mr/mc);
        CK(hipEventDestroy(a)); CK(hipEventDestroy(b)); CK(hipEventDestroy(c)); CK(hipEventDestroy(d));
    }
    auto med = [](std::vector<double> v) { return v[v.size()/2]; };
    double a = med(tc), b = med(tr);
    std::printf("MEDIAN: canonical %.3f | repacked %.3f | ratio %.3f (%s)\n",
                a, b, b/a, b < a ? "REPACKED FASTER" : "REPACKED SLOWER");
    CK(hipStreamDestroy(s));
    return 0;
}
