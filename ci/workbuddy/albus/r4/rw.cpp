// 我们的真实几何（n_expert=512, k=6）下：默认路径（gfx906 上 = wave kernel）vs S6 fast kernel，
// 逐 bit 比较 ids 与 weights。生产走的是 router_top10()，所以这一步是必须的。
#include <hip/hip_runtime.h>
#include "strata/kernels/router_top10.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>

#define CHECK(call)                                                                                                    \
    do {                                                                                                               \
        const hipError_t e_ = (call);                                                                                  \
        if (e_ != hipSuccess) {                                                                                        \
            std::fprintf(stderr, "%s: %s\n", #call, hipGetErrorString(e_));                                            \
            return 2;                                                                                                  \
        }                                                                                                              \
    } while (0)

namespace k = strata::kernels;

static int run_case(int n_expert, int topk, int rows, unsigned seed, const char* tag) {
    std::mt19937 rng(seed);
    std::normal_distribution<float> nd(0.f, 2.f);
    std::vector<float> lg((size_t) rows * n_expert);
    for (size_t i = 0; i < lg.size(); ++i) {
        const size_t r = i / n_expert;
        float x = nd(rng) * (r % 7 == 5 ? 40.0f : 1.0f);
        if (r % 3 == 1) x = std::round(x * 4.0f) / 4.0f;      // 大量并列
        if (r % 3 == 2) x = std::round(x * 64.0f) / 64.0f;    // 近似并列
        if (r % 1000 == 999 && (i % n_expert) == 77) x = NAN; // NaN 行
        if (r % 1000 == 998) x = 1.0f;                        // 全等行
        lg[i] = x;
    }
    const size_t out = (size_t) rows * topk;
    float* d_l = nullptr;
    CHECK(hipMalloc(&d_l, lg.size() * 4));
    CHECK(hipMemcpy(d_l, lg.data(), lg.size() * 4, hipMemcpyHostToDevice));

    const int NV = 3;   // 0 = 默认路径 router_top10()；1 = fast；2 = fast 强制串行
    float* d_w[NV] = {};
    int* d_i[NV] = {};
    std::vector<int> ids[NV];
    std::vector<float> w[NV];
    for (int v = 0; v < NV; ++v) {
        CHECK(hipMalloc(&d_w[v], out * 4));
        CHECK(hipMalloc(&d_i[v], out * 4));
        CHECK(hipMemset(d_w[v], 0x3c, out * 4));
        CHECK(hipMemset(d_i[v], 0x11, out * 4));
        bool ok = true;
        if (v == 0) {
            k::router_top10(d_l, rows, n_expert, topk, d_i[v], d_w[v], nullptr);
        } else {
            ok = k::router_top10_variant(d_l, rows, n_expert, topk, d_i[v], d_w[v], nullptr, v);
        }
        if (!ok) {
            std::printf("%s: variant %d refused\n", tag, v);
            return 2;
        }
        CHECK(hipDeviceSynchronize());
        ids[v].resize(out);
        w[v].resize(out);
        CHECK(hipMemcpy(ids[v].data(), d_i[v], out * 4, hipMemcpyDeviceToHost));
        CHECK(hipMemcpy(w[v].data(), d_w[v], out * 4, hipMemcpyDeviceToHost));
    }

    int bad_i = 0, bad_w = 0, bad_w_bits = 0;
    for (size_t i = 0; i < out; ++i) {
        if (ids[0][i] != ids[1][i]) ++bad_i;
        if (w[0][i] != w[1][i]) ++bad_w;
        if (std::memcmp(&w[0][i], &w[1][i], 4) != 0) ++bad_w_bits;
    }
    std::printf("%s: default-vs-fast  ids 差异 %d / %zu, weights 值差异 %d, weights 位差异 %d\n",
                tag, bad_i, out, bad_w, bad_w_bits);

    int bad_i2 = 0, bad_w2 = 0;
    for (size_t i = 0; i < out; ++i) {
        if (ids[0][i] != ids[2][i]) ++bad_i2;
        if (std::memcmp(&w[0][i], &w[2][i], 4) != 0) ++bad_w2;
    }
    std::printf("%s: default-vs-fast(串行) ids 差异 %d, weights 位差异 %d\n", tag, bad_i2, bad_w2);

    hipFree(d_l);
    for (int v = 0; v < NV; ++v) { hipFree(d_w[v]); hipFree(d_i[v]); }
    return (bad_i || bad_w_bits || bad_i2 || bad_w2) ? 1 : 0;
}

int main() {
    int rc = 0;
    rc |= run_case(512, 6, 65536, 1234u, "512 experts, k 6");
    rc |= run_case(512, 10, 8192, 99u, "512 experts, k 10");
    rc |= run_case(256, 8, 8192, 7u, "256 experts, k 8");
    std::printf(rc == 0 ? "RESULT: BITWISE IDENTICAL\n" : "RESULT: DIFFERENCES FOUND\n");
    return rc;
}
