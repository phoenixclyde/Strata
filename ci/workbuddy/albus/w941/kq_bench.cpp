// W941 / R61: production-shaped MMQ driver for PMC. One product, 16 experts x 1024 tokens = 16384 rows,
// Q4_K gate/up [1280, 2560] — the shape the prompt path actually runs at chunk 16384.
// Numbers are meaningless (random weight bytes); this only exists so rocprofv3 can sample VALUBusy on the kernel.
#include "strata/prefill/moe_mmq.hpp"
#include "ggml.h"

#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace mmq = strata::prefill::mmq;

static void ck(cudaError_t e, const char* what) {
    if (e != cudaSuccess) throw std::runtime_error(std::string(what) + ": " + cudaGetErrorString(e));
}

struct Dev {
    void* p = nullptr;
    explicit Dev(size_t bytes) { ck(cudaMalloc(&p, bytes), "cudaMalloc"); }
    ~Dev() { if (p) cudaFree(p); }
    Dev(const Dev&) = delete;
    Dev& operator=(const Dev&) = delete;
};

int main(int argc, char** argv) {
    const int n = argc > 1 ? std::atoi(argv[1]) : 16;          // experts in the group
    const int rows_per = argc > 2 ? std::atoi(argv[2]) : 1024;  // tokens per expert
    const int reps = argc > 3 ? std::atoi(argv[3]) : 3;
    // argv: n experts, rows_per expert, reps, type, out_rows, cols
    const int tcode = argc > 4 ? std::atoi(argv[4]) : 12;         // 12=Q4_K 7=Q5_1 8=Q8_0 14=Q6_K 13=Q5_K
    const ggml_type t = (ggml_type) tcode;
    const int64_t out_rows = argc > 5 ? std::atoll(argv[5]) : 1280;
    const int64_t cols = argc > 6 ? std::atoll(argv[6]) : 2560;
    const int rows = n * rows_per;
    try {
        if (!mmq::built() || !mmq::supported((int) t)) { std::printf("MMQ/Q4_K not in this build\n"); return 1; }

        cudaStream_t s = nullptr;
        ck(cudaStreamCreateWithFlags(&s, cudaStreamNonBlocking), "stream");

        const size_t eb = mmq::matrix_bytes((int) t, out_rows, cols);
        std::printf("shape: type=%d w=[%lld,%lld] n=%d rows/expert=%d total_rows=%d expert_bytes=%zu reps=%d\n", tcode,
                    (long long) out_rows, (long long) cols, n, rows_per, rows, eb, reps);

        std::vector<uint8_t> w((size_t) n * eb + 4096);
        std::mt19937 rng(941);
        for (auto& b : w) b = (uint8_t) (rng() & 0xff);
        std::vector<float> x((size_t) rows * cols);
        for (auto& v : x) v = (float) ((rng() % 2000) - 1000) / 1000.0f;
        std::vector<int32_t> bounds(n + 1, 0), ids(rows);
        for (int e = 0; e < n; ++e) bounds[e + 1] = bounds[e] + rows_per;
        for (int i = 0; i < rows; ++i) ids[i] = i;

        Dev dw(w.size()), dx(x.size() * 4), dxq(mmq::q8_bytes(rows, cols)), db((n + 1) * 4), did(rows * 4),
            dy((size_t) rows * out_rows * 4);

        ck(cudaMemcpy(dw.p, w.data(), w.size(), cudaMemcpyHostToDevice), "w");
        ck(cudaMemcpy(dx.p, x.data(), x.size() * 4, cudaMemcpyHostToDevice), "x");
        ck(cudaMemcpy(db.p, bounds.data(), (n + 1) * 4, cudaMemcpyHostToDevice), "bounds");
        ck(cudaMemcpy(did.p, ids.data(), (size_t) rows * 4, cudaMemcpyHostToDevice), "ids");
        ck(cudaDeviceSynchronize(), "inputs");

        mmq::quantize((const float*) dx.p, (const int32_t*) did.p, dxq.p, (int) t, cols, cols, rows, s);
        ck(cudaStreamSynchronize(s), "quantize");

        mmq::Product p;
        p.w = dw.p; p.type = (int) t; p.w_rows = out_rows; p.w_cols = cols; p.expert_bytes = eb; p.n = n;
        p.xq = dxq.p; p.bounds = (const int32_t*) db.p; p.ids = (const int32_t*) did.p;
        p.total_rows = rows; p.max_rows = rows_per; p.dst = (float*) dy.p; p.ld_dst = out_rows;

        mmq::Context ctx;
        ctx.run(p, s);   // warm-up: module load + first-launch cost, not measured
        ck(cudaStreamSynchronize(s), "warmup");
        for (int r = 0; r < reps; ++r) {
            cudaEvent_t a, b;
            ck(cudaEventCreate(&a), "ev"); ck(cudaEventCreate(&b), "ev");
            ck(cudaEventRecord(a, s), "rec");
            ctx.run(p, s);
            ck(cudaEventRecord(b, s), "rec");
            ck(cudaStreamSynchronize(s), "sync");
            float ms = 0;
            ck(cudaEventElapsedTime(&ms, a, b), "elapsed");
            double mac = (double) rows * out_rows * cols;
            std::printf("rep %d: %.3f ms  %.2f TMAC/s\n", r + 1, ms, mac / (ms * 1e9));
            ck(cudaEventDestroy(a), "ev"); ck(cudaEventDestroy(b), "ev");
        }
        ck(cudaStreamDestroy(s), "destroy");
        std::printf("bench done\n");
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "bench failed: %s\n", e.what());
        return 1;
    }
}
