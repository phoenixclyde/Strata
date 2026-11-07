// R55 probe: time qsa_block_topk at a 32K context and check its ids against qsa_block_topk_ref.
// Built twice: against the baseline qsa_select.cpp.o and against the ds_swizzle one.
#include <hip/hip_runtime.h>

#include "strata/kernels/qsa.hpp"
#include "strata/kernels/qsa_select.hpp"

#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

using namespace strata::kernels;

int main(int argc, char** argv) {
    const int64_t n_kv = argc > 1 ? std::atoll(argv[1]) : 32768;
    const int reps = argc > 2 ? std::atoi(argv[2]) : 200;
    const QsaShapes s = qsa_real_shapes();
    const int64_t n_bid = n_kv / s.idx_block;
    const int64_t max_blocks = n_bid + 1;
    const int64_t width = qsa_selection_width(n_kv, s);
    const int64_t cap = width;
    const int64_t nq = 1;

    std::mt19937 rng(1234);
    std::uniform_real_distribution<float> u(-8.f, 8.f);
    std::vector<float> h_scores((size_t) nq * max_blocks);
    for (auto& v : h_scores) v = u(rng);
    std::vector<int32_t> h_steps((size_t) nq * kStepCount, 0);
    h_steps[kStepPos] = (int32_t) (n_kv - 1);
    h_steps[kStepNKv] = (int32_t) n_kv;
    h_steps[kStepNBid] = (int32_t) n_bid;
    h_steps[kStepWidth] = (int32_t) width;

    float* d_scores = nullptr;
    int32_t *d_steps = nullptr, *d_ids = nullptr, *d_ref = nullptr;
    if (hipMalloc(&d_scores, h_scores.size() * sizeof(float)) != hipSuccess) return 2;
    if (hipMalloc(&d_steps, h_steps.size() * sizeof(int32_t)) != hipSuccess) return 2;
    if (hipMalloc(&d_ids, (size_t) nq * cap * sizeof(int32_t)) != hipSuccess) return 2;
    if (hipMalloc(&d_ref, (size_t) nq * cap * sizeof(int32_t)) != hipSuccess) return 2;
    hipMemcpy(d_scores, h_scores.data(), h_scores.size() * sizeof(float), hipMemcpyHostToDevice);
    hipMemcpy(d_steps, h_steps.data(), h_steps.size() * sizeof(int32_t), hipMemcpyHostToDevice);
    hipMemset(d_ids, 0xff, (size_t) nq * cap * sizeof(int32_t));

    qsa_block_topk_ref(d_scores, d_steps, nq, max_blocks, cap, s, d_ref, nullptr);
    hipDeviceSynchronize();

    qsa_block_topk(d_scores, d_steps, nq, max_blocks, cap, s, d_ids, nullptr);   // warm
    hipDeviceSynchronize();

    hipEvent_t e0, e1;
    hipEventCreate(&e0); hipEventCreate(&e1);
    hipEventRecord(e0);
    for (int i = 0; i < reps; ++i) qsa_block_topk(d_scores, d_steps, nq, max_blocks, cap, s, d_ids, nullptr);
    hipEventRecord(e1);
    hipEventSynchronize(e1);
    float ms = 0.f;
    hipEventElapsedTime(&ms, e0, e1);

    std::vector<int32_t> h_ids((size_t) nq * cap), h_ref((size_t) nq * cap);
    hipMemcpy(h_ids.data(), d_ids, h_ids.size() * sizeof(int32_t), hipMemcpyDeviceToHost);
    hipMemcpy(h_ref.data(), d_ref, h_ref.size() * sizeof(int32_t), hipMemcpyDeviceToHost);
    size_t bad = 0, n_used = 0;
    for (size_t i = 0; i < h_ids.size(); ++i) {
        if (h_ref[i] < 0) continue;                 // beyond the reference's selection
        ++n_used;
        if (h_ids[i] != h_ref[i]) ++bad;
    }
    std::printf("n_kv=%lld n_bid=%lld width=%lld cap=%lld  %.4f ms/call  ids_checked=%zu mismatched=%zu  %s\n",
                (long long) n_kv, (long long) n_bid, (long long) width, (long long) cap, ms / reps, n_used, bad,
                bad == 0 ? "IDS EQUAL" : "IDS DIFFER");
    hipFree(d_scores); hipFree(d_steps); hipFree(d_ids); hipFree(d_ref);
    return bad == 0 ? 0 : 1;
}
