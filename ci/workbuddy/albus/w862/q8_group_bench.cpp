// q8_group_bench.cpp -- W862: is the decode GEMV group limited by per-kernel parallelism?
//
// Same production entry point as q8_gemv_bench (K::native_mmvq), same shapes, same cache-missing
// trick. The only variable is how the independent GEMVs of one layer are issued:
//   serial    : all of them on one stream, one after another (what the engine does today)
//   streams-N : N hip streams, round-robin, so independent matrices can co-reside on the CUs
//
// If streams-N is much faster than serial, the layer's cost is per-launch parallelism (too few
// waves to fill 60 CUs), and the fix is to make the group one grid -- not to retune a kernel that
// already reaches 98 % of bandwidth on the head.
//
//   build/q8_group_bench [--iters 50] [--bw 711] [--group all|same]
#include "strata/kernels/native_mmvq.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <random>
#include <string>
#include <vector>

namespace K = strata::kernels;
// lab-only: exists in the patched copy of native_mmvq.cu (W862), not in the production archive
namespace strata { namespace kernels {
void native_mmvq_set_wave_rows(int n);
int native_mmvq_wave_rows();
} }

static int G_COLS = 1;   // 生产 decode 是投机验证窗口：--spec 4 => 一次 5..6 列
static void mmvq(const void* w, void* xq, float* y, int n_in, int n_out, cudaStream_t s) {
    K::native_mmvq(8, w, xq, y, n_in, n_out, G_COLS, s);
}

namespace {
struct Shape { const char* what; int n_in, n_out; };
// The model's dense Q8_0 matrices, one layer's worth, in the order the engine hits them.
const Shape SHAPES[] = {
    {"GDN qkv      2560->10240", 2560, 10240}, {"GDN gate     2560->6144", 2560, 6144},
    {"GDN/QSA out  6144->2560", 6144, 2560},   {"QSA q        2560->12288", 2560, 12288},
    {"QSA k/v      2560->512", 2560, 512},     {"HC down     10240->320", 10240, 320},
    {"HC up         320->10240", 320, 10240},  {"shared g/u   2560->640", 2560, 640},
    {"shared down   640->2560", 640, 2560},
};
constexpr int NSHAPE = sizeof(SHAPES) / sizeof(SHAPES[0]);
constexpr int HEAD_IDX = -1;   // head is 15x the rest and already at 98 %; not part of a layer

void ck(cudaError_t e, const char* w) {
    if (e != cudaSuccess) { std::fprintf(stderr, "%s: %s\n", w, cudaGetErrorString(e)); std::exit(1); }
}

struct Mat {
    const Shape* s;
    std::vector<void*> w;   // several copies so the reads miss the last-level cache
    size_t bytes = 0;
    void* xq = nullptr;     // this matrix's own quantized activation (n_in differs per matrix)
};

double run_serial(const std::vector<Mat>& ms, const std::vector<int>& idx, std::vector<float*>& y,
                  cudaStream_t s, int iters) {
    for (int i = 0; i < 3; ++i)
        for (int k : idx) mmvq(ms[k].w[i % ms[k].w.size()], ms[k].xq, y[k], ms[k].s->n_in, ms[k].s->n_out, s);
    cudaEvent_t e0, e1; cudaEventCreate(&e0); cudaEventCreate(&e1);
    cudaEventRecord(e0, s);
    for (int it = 0; it < iters; ++it)
        for (int k : idx) mmvq(ms[k].w[it % ms[k].w.size()], ms[k].xq, y[k], ms[k].s->n_in, ms[k].s->n_out, s);
    cudaEventRecord(e1, s);
    ck(cudaEventSynchronize(e1), "sync");
    float ms_v = 0; cudaEventElapsedTime(&ms_v, e0, e1);
    cudaEventDestroy(e0); cudaEventDestroy(e1);
    return 1000.0 * ms_v / iters;   // us per group
}

double run_streams(const std::vector<Mat>& ms, const std::vector<int>& idx, std::vector<float*>& y,
                   std::vector<cudaStream_t>& ss, int iters) {
    const int S = (int) ss.size();
    cudaEvent_t e0, e1; cudaEventCreate(&e0); cudaEventCreate(&e1);
    std::vector<cudaEvent_t> mark(S);
    for (auto& m : mark) cudaEventCreate(&m);
    for (int i = 0; i < 3; ++i)
        for (size_t j = 0; j < idx.size(); ++j) {
            const int k = idx[j];
            mmvq(ms[k].w[i % ms[k].w.size()], ms[k].xq, y[k], ms[k].s->n_in, ms[k].s->n_out, ss[j % S]);
        }
    for (auto s : ss) ck(cudaStreamSynchronize(s), "warm");
    cudaEventRecord(e0, ss[0]);
    for (int j = 1; j < S; ++j) ck(cudaStreamWaitEvent(ss[j], e0, 0), "wait0");
    for (int it = 0; it < iters; ++it)
        for (size_t j = 0; j < idx.size(); ++j) {
            const int k = idx[j];
            mmvq(ms[k].w[it % ms[k].w.size()], ms[k].xq, y[k], ms[k].s->n_in, ms[k].s->n_out, ss[j % S]);
        }
    for (int j = 1; j < S; ++j) {   // fold every stream's tail back onto stream 0
        cudaEventRecord(mark[j], ss[j]);
        ck(cudaStreamWaitEvent(ss[0], mark[j], 0), "join");
    }
    cudaEventRecord(e1, ss[0]);
    ck(cudaEventSynchronize(e1), "sync");
    float ms_v = 0; cudaEventElapsedTime(&ms_v, e0, e1);
    cudaEventDestroy(e0); cudaEventDestroy(e1);
    for (auto& m : mark) cudaEventDestroy(m);
    return 1000.0 * ms_v / iters;
}
}  // namespace

int main(int argc, char** argv) {
    int iters = 50;
    double bw = 711.0;
    std::string group = "all";
    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--iters" && i + 1 < argc) iters = std::atoi(argv[++i]);
        else if (a == "--bw" && i + 1 < argc) bw = std::atof(argv[++i]);
        else if (a == "--group" && i + 1 < argc) group = argv[++i];
        else if (a == "--cols" && i + 1 < argc) G_COLS = std::atoi(argv[++i]);
        else if (a == "--rows" && i + 1 < argc) K::native_mmvq_set_wave_rows(std::atoi(argv[++i]));
    }
    cudaDeviceProp prop;
    ck(cudaGetDeviceProperties(&prop, 0), "props");
    int cus = 0;
    ck(cudaDeviceGetAttribute(&cus, cudaDevAttrMultiProcessorCount, 0), "cus");
    std::printf("q8_group_bench: %s | %d CU | peak ref %.0f GB/s | ncols=%d rows=%d\n", prop.name, cus, bw, G_COLS, K::native_mmvq_wave_rows());

    std::mt19937 rng(7);
    std::vector<Mat> ms(NSHAPE);
    double total_mb = 0;
    for (int i = 0; i < NSHAPE; ++i) {
        Mat& m = ms[i];
        m.s = &SHAPES[i];
        const size_t bytes = (size_t) SHAPES[i].n_out * (SHAPES[i].n_in / 32) * 34;
        m.bytes = bytes;
        // Production holds 33.5 GB of the card's 34.3 GB, so keep this bench under ~350 MB and still
        // overflow the 4 MB L2: >= 2 copies of every matrix, 8 for the small ones.
        const int copies = (int) std::max<size_t>(2, std::min<size_t>(8, ((size_t) 64 << 20) / bytes));
        std::vector<uint8_t> host(bytes);
        for (size_t b = 0; b < bytes; b += 34) {
            host[b] = 0x1f; host[b + 1] = 0x21;
            for (int k = 0; k < 32; ++k) host[b + 2 + k] = (uint8_t) (rng() & 0xff);
        }
        m.w.resize(copies);
        for (auto& p : m.w) {
            ck(cudaMalloc(&p, bytes), "malloc w");
            ck(cudaMemcpy(p, host.data(), bytes, cudaMemcpyHostToDevice), "copy w");
        }
        total_mb += bytes / 1e6;
    }

    cudaStream_t s0; ck(cudaStreamCreate(&s0), "s0");
    // one quantized activation per distinct n_in (a layer's 2560-vector feeds five matrices; the
    // others are the residual-branch widths). Quantized once, exactly as the engine shares it.
    std::vector<float*> xs;
    for (int i = 0; i < NSHAPE; ++i) {
        const int n = SHAPES[i].n_in;
        float* xp = nullptr;
        bool seen = false;
        for (int j = 0; j < i; ++j) if (SHAPES[j].n_in == n && ms[j].xq) { ms[i].xq = ms[j].xq; seen = true; break; }
        if (seen) continue;
        std::vector<float> xh((size_t) n * G_COLS);
        for (auto& v : xh) v = std::normal_distribution<float>(0.f, 1.f)(rng);
        ck(cudaMalloc(&xp, xh.size() * 4), "x");
        ck(cudaMemcpy(xp, xh.data(), xh.size() * 4, cudaMemcpyHostToDevice), "x copy");
        ck(cudaMalloc(&ms[i].xq, K::native_q8_1_bytes(n, G_COLS)), "xq");
        K::native_quantize_q8_1(xp, ms[i].xq, n, G_COLS, s0);
        xs.push_back(xp);
    }
    ck(cudaStreamSynchronize(s0), "quant");

    std::vector<float*> y(NSHAPE);
    for (int i = 0; i < NSHAPE; ++i) ck(cudaMalloc(&y[i], (size_t) SHAPES[i].n_out * G_COLS * 4), "y");

    // the group whose input is the same 2560-vector: GDN qkv, GDN gate, QSA q, QSA k/v, shared g/u
    std::vector<int> same = {0, 1, 3, 4, 7};
    std::vector<int> all(NSHAPE);
    for (int i = 0; i < NSHAPE; ++i) all[i] = i;
    const std::vector<int>& idx = (group == "same") ? same : all;

    double mb = 0;
    for (int k : idx) mb += ms[k].bytes / 1e6;
    std::printf("\ngroup=%s: %zu matrices, %.2f MB, x=2560 (1 vector, quantized once)\n", group.c_str(), idx.size(), mb);

    if (group == "check") {   // R>1 必须逐位等价：每行的归约顺序没变，只是同一波里多算几行
        std::vector<float> a, b;
        int bad = 0;
        const int want = K::native_mmvq_wave_rows();   // --rows 的取值，必须在改成 1 之前拿
        if (want == 1) { std::printf("  --rows 1 没有对照；用 --rows 2/4 跑这个模式\n"); return 2; }
        for (int k = 0; k < NSHAPE; ++k) {
            const size_t n = (size_t) SHAPES[k].n_out * G_COLS;
            a.assign(n, -1.f); b.assign(n, -2.f);
            K::native_mmvq_set_wave_rows(1);
            K::native_mmvq(8, ms[k].w[0], ms[k].xq, y[k], SHAPES[k].n_in, SHAPES[k].n_out, G_COLS, s0);
            ck(cudaMemcpy(a.data(), y[k], n * 4, cudaMemcpyDeviceToHost), "d2h a");
            K::native_mmvq_set_wave_rows(want);
            K::native_mmvq(8, ms[k].w[0], ms[k].xq, y[k], SHAPES[k].n_in, SHAPES[k].n_out, G_COLS, s0);
            ck(cudaMemcpy(b.data(), y[k], n * 4, cudaMemcpyDeviceToHost), "d2h b");
            size_t diff = 0; double maxd = 0;
            for (size_t i = 0; i < n; ++i) {
                if (a[i] != b[i]) { ++diff; maxd = std::max(maxd, (double) std::fabs(a[i] - b[i])); }
            }
            if (diff) ++bad;
            std::printf("  %-24s %s  diff=%zu/%zu  max|d|=%.3g\n", SHAPES[k].what,
                        diff ? "MISMATCH" : "bitwise-equal", diff, n, maxd);
        }
        std::printf("  => %s\n", bad ? "NOT EQUIVALENT" : "all bitwise equal");
        for (auto p2 : y) cudaFree(p2);
        for (auto p2 : xs) cudaFree(p2);
        for (auto& m : ms) { if (m.xq) cudaFree(m.xq); for (auto q : m.w) cudaFree(q); }
        cudaStreamDestroy(s0);
        return bad ? 1 : 0;
    }
    if (group == "single") {   // 逐个隔离：和 W861 那张表同口径，用来核对基线
        double sum = 0;
        for (int k : idx) {
            std::vector<int> one = {k};
            const double t = run_serial(ms, one, y, s0, iters);
            const double gbs = ms[k].bytes / 1e3 / t * 1e3 / 1e3;
            std::printf("  %-24s %8.2f MB %8.1f us %7.1f GB/s %5.1f%%\n", SHAPES[k].what, ms[k].bytes / 1e6,
                        t, ms[k].bytes / 1e3 / t * 1e3, 100.0 * (ms[k].bytes / 1e3 / t * 1e3) / bw);
            sum += t;
        }
        std::printf("  sum of isolated   : %8.1f us  (%.2f MB per layer)\n", sum, mb);
        }
    const double t_serial = run_serial(ms, idx, y, s0, iters);
    std::printf("  serial   1 stream : %8.1f us  %6.1f GB/s  %5.1f%% of bw\n", t_serial, mb * 1e3 / t_serial,
                100.0 * (mb * 1e3 / t_serial) / bw);
    for (int S : {2, 3, 5, 6, 9}) {
        if (S > (int) idx.size()) continue;
        std::vector<cudaStream_t> ss(S);
        for (auto& s : ss) ck(cudaStreamCreate(&s), "stream");
        const double t = run_streams(ms, idx, y, ss, iters);
        const double gbs = mb * 1e3 / t;
        std::printf("  streams %d        : %8.1f us  %6.1f GB/s  %5.1f%% of bw   (%.2fx)\n", S, t, gbs,
                    100.0 * gbs / bw, t_serial / t);
        for (auto s : ss) cudaStreamDestroy(s);
    }
    // ---- upper bound: the same 5 matrices as ONE launch -------------------------------
    // All five take the same 2560-vector and use the same Q8_0 block layout, so concatenating
    // their rows is exactly what a fused kernel would compute. One grid of 29624 rows = 7406
    // blocks instead of 5 launches of 160..3072 blocks.
    if (group == "same") {
        int rows = 0;
        for (int k : same) rows += SHAPES[k].n_out;
        size_t cbytes = (size_t) rows * (2560 / 32) * 34;
        void* wc = nullptr;
        ck(cudaMalloc(&wc, cbytes), "malloc concat");
        std::vector<uint8_t> hb(cbytes);
        for (size_t b = 0; b < cbytes; b += 34) { hb[b] = 0x1f; hb[b + 1] = 0x21; }
        ck(cudaMemcpy(wc, hb.data(), cbytes, cudaMemcpyHostToDevice), "copy concat");
        float* yc = nullptr;
        ck(cudaMalloc(&yc, (size_t) rows * G_COLS * 4), "y concat");
        for (int i = 0; i < 3; ++i) mmvq(wc, ms[same[0]].xq, yc, 2560, rows, s0);
        cudaEvent_t a0, a1; cudaEventCreate(&a0); cudaEventCreate(&a1);
        cudaEventRecord(a0, s0);
        for (int it = 0; it < iters; ++it) mmvq(wc, ms[same[0]].xq, yc, 2560, rows, s0);
        cudaEventRecord(a1, s0);
        ck(cudaEventSynchronize(a1), "sync");
        float msv = 0; cudaEventElapsedTime(&msv, a0, a1);
        const double t1 = 1000.0 * msv / iters, g1 = mb * 1e3 / t1;
        std::printf("  FUSED 1 grid     : %8.1f us  %6.1f GB/s  %5.1f%% of bw   (%.2fx vs serial)\n", t1, g1,
                    100.0 * g1 / bw, t_serial / t1);
        cudaFree(wc); cudaFree(yc);
        cudaEventDestroy(a0); cudaEventDestroy(a1);
    }
    for (auto p : y) cudaFree(p);
    for (auto p : xs) cudaFree(p);
    for (auto& m : ms) if (m.xq) cudaFree(m.xq);
    cudaStreamDestroy(s0);
    for (auto& m : ms) for (auto p : m.w) cudaFree(p);
    return 0;
}
