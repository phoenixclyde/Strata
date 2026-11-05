// W1003b: type x shape x width sweep.
//
// W1001/W1003a measured ONE type (Q5_1) on two shapes. Production is
// ud-q4_k_xl — the experts are a Q4_K / Q5_K / Q6_K mix — and the gate/up
// product is a SINGLE 1280-row call (prefill.cpp:5300 `gu.w_rows = 1280`),
// not the 640-row half the first sweep used. This bench closes both gaps.
//
// Weights here are RANDOM BYTES of the correct repacked geometry: the timing
// only depends on the load/scale planes, never on the values, so this is a
// valid *timing* probe and an INVALID correctness probe. Correctness is C5's
// job (bit-exact vs canonical), later.
#include "repack/repack-kernels.cuh"
#include "strata/prefill/moe_mmq.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <random>
#include <algorithm>
#include <hip/hip_runtime.h>

namespace mmq = strata::prefill::mmq;

#define CK(x) do { hipError_t e = (x); if (e != hipSuccess) { \
    std::fprintf(stderr, "HIP %s:%d: %s\n", __FILE__, __LINE__, hipGetErrorString(e)); std::exit(1); } } while (0)

template <typename T> struct D {
    T * p = nullptr;
    explicit D(size_t bytes) { CK(hipMalloc(&p, bytes)); }
    ~D() { if (p) hipFree(p); }
};

struct Plan {
    int max_tiles = 0;
    std::vector<repack_tile_meta> meta;
    std::vector<int32_t> tile_off;
};

static Plan make_plan(const std::vector<int32_t> & bounds, int n, int BN, size_t rows) {
    Plan p;
    p.max_tiles = (int) (rows / (size_t) BN) + n + 4;
    p.meta.resize(p.max_tiles);
    p.tile_off.assign(n + 1, 0);
    int acc = 0;
    for (int e = 0; e < n; ++e) {
        const int cnt = bounds[e + 1] - bounds[e], nt = (cnt + BN - 1) / BN;
        for (int t = 0; t < nt && acc + t < p.max_tiles; ++t) {
            p.meta[acc + t].expert = (uint32_t) e;
            p.meta[acc + t].a_base = (uint32_t) bounds[e] + (uint32_t) t * BN;
        }
        acc += nt; p.tile_off[e + 1] = acc;
    }
    return p;
}

static double median(std::vector<double> v) { std::sort(v.begin(), v.end()); return v[v.size() / 2]; }

// One (type, shape) sweep. Kept as a template so the kernel selection below
// stays a compile-time constant, exactly as the production port will need it.
template <ggml_type T, int KN>
static void sweep(int n, int reps, int out_rows, int cols, const char * label) {
    const size_t stride = repack_gcn_nbytes(T, cols, out_rows);
    const size_t eb     = mmq::matrix_bytes((int) T, out_rows, cols);
    const size_t max_rows_per = 1024, rows_max = (size_t) n * max_rows_per;

    std::mt19937 rng(1003 + (int) T);
    std::vector<uint8_t> w((size_t) n * eb);
    for (auto & b : w) b = (uint8_t) (rng() & 0xff);
    std::vector<uint8_t> rep((size_t) n * stride);
    for (auto & b : rep) b = (uint8_t) (rng() & 0xff);
    std::vector<float> x(rows_max * cols);
    for (auto & v : x) v = (float) ((rng() % 2000) - 1000) / 1000.0f;

    std::printf("# %s: type=%d out=%d K=%d experts=%d canonical_bytes=%zu repack_stride=%zu\n",
                label, (int) T, out_rows, cols, n, eb, stride);
    std::printf("# rows_per\tcanonical_ms\tw32_ms\tratio32\tw64_ms\tratio64\twinner\n");

    D<uint8_t> dw(w.size()), dwr(rep.size()), dx(rows_max * cols * 4),
               dxq(mmq::q8_bytes((int64_t) rows_max, cols) * 2),
               dy(rows_max * out_rows * 4);
    D<int32_t> did(rows_max * 4), db((n + 1) * 4);
    CK(hipMemcpy(dw.p,  w.data(),   w.size(),     hipMemcpyHostToDevice));
    CK(hipMemcpy(dwr.p, rep.data(), rep.size(),   hipMemcpyHostToDevice));
    CK(hipMemcpy(dx.p,  x.data(),   x.size() * 4, hipMemcpyHostToDevice));

    hipStream_t s; CK(hipStreamCreateWithFlags(&s, hipStreamNonBlocking));
    std::vector<int32_t> ids(rows_max);
    for (size_t i = 0; i < rows_max; ++i) ids[i] = (int32_t) i;
    CK(hipMemcpy(did.p, ids.data(), rows_max * 4, hipMemcpyHostToDevice));
    mmq::quantize((const float *) dx.p, did.p, dxq.p, (int) T, cols, cols, (int64_t) rows_max, s);
    CK(hipStreamSynchronize(s));

    const int points[] = {32, 128, 320, 512, 1024};
    for (int rows_per : points) {
        const size_t rows = (size_t) n * rows_per;
        std::vector<int32_t> bounds(n + 1, 0);
        for (int e = 0; e < n; ++e) bounds[e + 1] = bounds[e] + rows_per;
        CK(hipMemcpy(db.p, bounds.data(), (n + 1) * 4, hipMemcpyHostToDevice));

        Plan p32 = make_plan(bounds, n, 32, rows);
        Plan p64 = make_plan(bounds, n, 64 * MMQ_RP_Q8_TN, rows);
        D<int32_t> dto32((n + 1) * 4), dto64((n + 1) * 4);
        D<repack_tile_meta> dm32(sizeof(repack_tile_meta) * p32.max_tiles),
                            dm64(sizeof(repack_tile_meta) * p64.max_tiles);
        CK(hipMemcpy(dto32.p, p32.tile_off.data(), (n + 1) * 4, hipMemcpyHostToDevice));
        CK(hipMemcpy(dto64.p, p64.tile_off.data(), (n + 1) * 4, hipMemcpyHostToDevice));
        CK(hipMemcpy(dm32.p,  p32.meta.data(), sizeof(repack_tile_meta) * p32.max_tiles, hipMemcpyHostToDevice));
        CK(hipMemcpy(dm64.p,  p64.meta.data(), sizeof(repack_tile_meta) * p64.max_tiles, hipMemcpyHostToDevice));

        mmq::Product p;
        p.w = dw.p; p.type = (int) T; p.w_rows = out_rows; p.w_cols = cols;
        p.expert_bytes = eb; p.n = n;
        p.xq = dxq.p; p.bounds = db.p; p.ids = did.p;
        p.total_rows = (int) rows; p.max_rows = rows_per; p.dst = (float *) dy.p; p.ld_dst = out_rows;
        mmq::Context ctx;

        const dim3 g32((out_rows + MMQ_RP_Q8_BM - 1) / MMQ_RP_Q8_BM, p32.max_tiles, 1);
        const dim3 g64((out_rows + MMQ_RP_Q8_BM - 1) / MMQ_RP_Q8_BM, p64.max_tiles, 1);
        const dim3 b32(32, MMQ_RP_Q8_NROW_LANES * 2), b64(64, MMQ_RP_Q8_NROW_LANES);

        auto run32 = [&]() {
            mmq_gemm_repacked_w32<true, 1, MMQ_RP_Q8_NROW_LANES * 2, T>
                <<<g32, b32, 0, s>>>(dwr.p, (const block_q8_1 *) dxq.p, (float *) dy.p,
                    (uint32_t) cols, (uint32_t) out_rows, (uint32_t) rows,
                    did.p, did.p, db.p, dto32.p, dm32.p, (uint32_t) n, stride, (uint32_t) out_rows);
        };
        auto run64 = [&]() {
            mmq_gemm_repacked<true, MMQ_RP_Q8_TN, MMQ_RP_Q8_NROW_LANES, T>
                <<<g64, b64, 0, s>>>(dwr.p, (const block_q8_1 *) dxq.p, (float *) dy.p,
                    (uint32_t) cols, (uint32_t) out_rows, (uint32_t) rows,
                    did.p, did.p, db.p, dto64.p, dm64.p, (uint32_t) n, stride, (uint32_t) out_rows);
        };

        run32(); run64(); ctx.run(p, s); CK(hipStreamSynchronize(s));
        hipError_t e = hipGetLastError();
        if (e != hipSuccess) { std::fprintf(stderr, "launch %s: %s\n", label, hipGetErrorString(e)); return; }

        std::vector<double> tc, t32, t64;
        for (int r = 0; r < reps; ++r) {
            hipEvent_t e0, e1;
            CK(hipEventCreate(&e0)); CK(hipEventCreate(&e1));
            CK(hipEventRecord(e0, s)); ctx.run(p, s); CK(hipEventRecord(e1, s));
            CK(hipStreamSynchronize(s)); float mc = 0; CK(hipEventElapsedTime(&mc, e0, e1));
            CK(hipEventRecord(e0, s)); run32();      CK(hipEventRecord(e1, s));
            CK(hipStreamSynchronize(s)); float m32 = 0; CK(hipEventElapsedTime(&m32, e0, e1));
            CK(hipEventRecord(e0, s)); run64();      CK(hipEventRecord(e1, s));
            CK(hipStreamSynchronize(s)); float m64 = 0; CK(hipEventElapsedTime(&m64, e0, e1));
            tc.push_back(mc); t32.push_back(m32); t64.push_back(m64);
            CK(hipEventDestroy(e0)); CK(hipEventDestroy(e1));
        }
        const double c = median(tc), a = median(t32), b = median(t64);
        const char * win = (a <= b && a < c) ? "w32" : (b < a && b < c) ? "w64" : "canonical";
        std::printf("%d\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%s\n", rows_per, c, a, a / c, b, b / c, win);
        std::fflush(stdout);
    }
    std::printf("\n");
    CK(hipStreamDestroy(s));
    (void) KN;
}

int main(int argc, char ** argv) {
    const int n    = argc > 1 ? std::atoi(argv[1]) : 16;
    const int reps = argc > 2 ? std::atoi(argv[2]) : 5;
    // argv[3]: shape. gu = the single 1280-row gate+up call; dn = the 2560-row down call.
    const char * shape = argc > 3 ? argv[3] : "gu";
    const int out_rows = std::strcmp(shape, "dn") == 0 ? 2560 : 1280;
    const int cols     = std::strcmp(shape, "dn") == 0 ? 640 : 2560;

    sweep<GGML_TYPE_Q5_1, 0>(n, reps, out_rows, cols, shape);   // control: W1001's type
    sweep<GGML_TYPE_Q4_K, 0>(n, reps, out_rows, cols, shape);
    sweep<GGML_TYPE_Q5_K, 0>(n, reps, out_rows, cols, shape);
    sweep<GGML_TYPE_Q6_K, 0>(n, reps, out_rows, cols, shape);
    sweep<GGML_TYPE_Q8_0, 0>(n, reps, out_rows, cols, shape);
    return 0;
}
