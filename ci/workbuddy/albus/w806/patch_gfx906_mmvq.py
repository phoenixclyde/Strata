#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W806: 把上游 PR #4158（gfx906 小 chunk 的 native MMVQ dense 投影）+ 其前置 #4156（hip_compat 的 stream 优先级映射）
   移植到本机的 v0.2.4.2 / 0.1.49.2 源码树。

   为什么是"移植"而不是 git apply：#4158 的 base 是 0.1.50，我们是 0.1.49.2；逐个改动都只有几行，
   且用到的 `strata::kernels::native_mmvq*` API 在 0.1.49.2 里逐字存在（已核对签名），所以按锚点插入即可。

   用法：
     patch_gfx906_mmvq.py <tree> --check     # 只检查当前状态（0=未打，已打=报告）
     patch_gfx906_mmvq.py <tree>             # 打补丁
   纪律：每个锚点必须**恰好出现一次**，否则拒绝改（宁可失败，也不误改）。
"""
import sys, os

GUARD = ("    if (native_mmvq(X, ggml_type, W_blocks, Y, T, N, K, ldy, beta, ldx)) return;\n")

IMPL = r'''namespace {
__global__ void pf_mmvq_widen(const __half* __restrict__ in, float* __restrict__ out, int64_t n) {
    const int64_t i = (int64_t) blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) out[i] = __half2float(in[i]);
}
// values per block of a GGML type (native_mmvq.hpp's ids): the K the MMVQ kernels need a whole number of
int64_t pf_mmvq_block(int type) {
    switch (type) {
        case 2: case 6: case 8: case 20: return 32;   // Q4_0, Q5_0, Q8_0, IQ4_NL
        case 42: return 64;                           // Q2_0
        default: return 256;                          // Q3_K .. Q6_K, IQ4_XS
    }
}
}  // namespace

bool Gemm::native_mmvq(const uint16_t* X, int ggml_type, const void* W_blocks, float* Y, int64_t T, int64_t N, int64_t K,
                       int64_t ldy, float beta, int64_t ldx) {
    static const bool on = [] { const char* v = std::getenv("STRATA_PF_MMVQ"); return v && v[0] == '1'; }();
    static const int64_t max_t = [] {
        const char* v = std::getenv("STRATA_PF_MMVQ_MAX_T");
        return v ? std::max<int64_t>(1, std::atoll(v)) : (int64_t) 256;   // the gfx906 turn sweep: 256 helps, 512+ slows ~480-token chunks
    }();
    if (!on || mmvq_failed_ || T < 1 || T > max_t || beta != 0.0f || (ldx != 0 && ldx != K) || (ldy != 0 && ldy != N) ||
        N < 1 || K < 1 || !strata::kernels::native_mmvq_supported(ggml_type) || K % pf_mmvq_block(ggml_type) != 0)
        return false;
    // one workspace of the fixed cap, allocated at the first use and never grown: growing would free it (a device-wide
    // sync) in the middle of a prompt.  A failed allocation turns the path off for this Gemm (no retry per projection).
    constexpr size_t kCap = 16u << 20;
    if (!mmvq_buf_) {
        if (cudaMalloc(&mmvq_buf_, kCap) != cudaSuccess) {
            (void) cudaGetLastError();
            mmvq_buf_ = nullptr;
            mmvq_failed_ = true;
            return false;
        }
        mmvq_bytes_ = kCap;
    }
    const size_t per_tok = (size_t) K * 4 + strata::kernels::native_q8_1_bytes((int) K, 1);
    const int64_t slice = std::min<int64_t>({T, 256, (int64_t) ((kCap - 256) / per_tok)});
    if (slice < 1) return false;
    const size_t f32_bytes = ((size_t) slice * K * 4 + 255) & ~(size_t) 255;
    float* const xf = static_cast<float*>(mmvq_buf_);
    uint8_t* const xq = static_cast<uint8_t*>(mmvq_buf_) + f32_bytes;
    const size_t q_col = strata::kernels::native_q8_1_bytes((int) K, 1);
    const cudaStream_t s = (cudaStream_t) stream_;
    for (int64_t t0 = 0; t0 < T; t0 += slice) {
        const int64_t n = std::min<int64_t>(slice, T - t0);
        pf_mmvq_widen<<<(unsigned) ((n * K + 255) / 256), 256, 0, s>>>(reinterpret_cast<const __half*>(X + t0 * K), xf,
                                                                        n * K);
        // the quantizer takes 1..8 columns; Q8_1 blocks are per 32 values and column j's sit at j * K / 32, so the
        // slice as ONE column of n * K values is byte for byte the n columns
        strata::kernels::native_quantize_q8_1(xf, xq, (int) (n * K), 1, stream_);
        for (int64_t c = 0; c < n; c += 8)
            strata::kernels::native_mmvq(ggml_type, W_blocks, xq + (size_t) c * q_col, Y + (t0 + c) * N, (int) K, (int) N,
                                         (int) std::min<int64_t>(8, n - c), stream_);
    }
    return true;
}

'''

DECL = r'''    /// STRATA_PF_MMVQ=1 (opt-in): native()'s product for a small chunk (T <= STRATA_PF_MMVQ_MAX_T, default 256) through
    /// decode's native MMVQ on the GGUF blocks, 8 token columns per call, the activations through Q8_1 - no dequantized
    /// weight, no GEMM.  Only beta = 0, contiguous X and Y (ldx 0 or K, ldy 0 or N), a type native_mmvq_supported()
    /// takes and a K that is a whole number of its blocks.  true: Y written; false: declined, nothing written.
    bool native_mmvq(const uint16_t* X, int ggml_type, const void* W_blocks, float* Y, int64_t T, int64_t N, int64_t K,
                     int64_t ldy = 0, float beta = 0.0f, int64_t ldx = 0);

'''

MEMBERS = r'''    void* mmvq_buf_ = nullptr;      // native_mmvq: an FP32 slice of X and its Q8_1 blocks (16 MiB, allocated once)
    size_t mmvq_bytes_ = 0;
    bool mmvq_failed_ = false;      // the workspace could not be allocated: the path stays off for this Gemm
'''

CU_DTOR_ANCHOR = "    if (unpadded_x_) cudaFree(unpadded_x_);\n"
CU_INC_ANCHOR = '#include "strata/kernels/dequant_bf16.hpp"\n'
CU_NATIVE_SIG = ("void Gemm::native(const uint16_t* X, int ggml_type, const void* W_blocks, float* Y, int64_t T, int64_t N, int64_t K,\n"
                 "                  int64_t ldy, float beta, int64_t ldx) {\n")
CU_GUARD_OLD = CU_NATIVE_SIG + "#ifdef STRATA_USE_HIP\n"
CU_GUARD_NEW = CU_NATIVE_SIG + GUARD + "#ifdef STRATA_USE_HIP\n"
HPP_DECL_ANCHOR = "    /// HIP gfx103x (prompt_f16()): bf16() takes X as the FP16 image the prompt path's kernels write (set_act_f16),\n"
HPP_MEM_ANCHOR = "    void* mmq_buf_ = nullptr;\n"
HIP_DEF_ANCHOR = "#define cudaStreamCreateWithFlags hipStreamCreateWithFlags\n"
HIP_DEF_NEW = (HIP_DEF_ANCHOR +
               "#define cudaStreamCreateWithPriority hipStreamCreateWithPriority\n"
               "#define cudaDeviceGetStreamPriorityRange hipDeviceGetStreamPriorityRange\n")


def edit(path, pairs, tag):
    s = open(path, encoding="utf-8").read()
    n = 0
    for old, new in pairs:
        c = s.count(old)
        if c != 1:
            raise SystemExit("!! %s: 锚点出现 %d 次（必须恰好 1 次）: %r" % (path, c, old[:70]))
        s = s.replace(old, new, 1)
        n += 1
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    print("  patched %-52s %d 处  (%s)" % (os.path.basename(path), n, tag))
    return n


def check(tree):
    cu = os.path.join(tree, "src/prefill/gemm.cu")
    hpp = os.path.join(tree, "include/strata/prefill/gemm.hpp")
    hip = os.path.join(tree, "include/strata/platform/hip_compat/strata_hip.h")
    got = {
        "gemm.cu::native_mmvq 定义": open(cu, encoding="utf-8").read().count("bool Gemm::native_mmvq("),
        "gemm.cu::native 守卫": open(cu, encoding="utf-8").read().count("if (native_mmvq(X, ggml_type"),
        "gemm.cu::include": open(cu, encoding="utf-8").read().count('#include "strata/kernels/native_mmvq.hpp"'),
        "gemm.cu::dtor free": open(cu, encoding="utf-8").read().count("if (mmvq_buf_) cudaFree(mmvq_buf_);"),
        "gemm.hpp::声明": open(hpp, encoding="utf-8").read().count("bool native_mmvq(const uint16_t* X"),
        "gemm.hpp::成员": open(hpp, encoding="utf-8").read().count("size_t mmvq_bytes_ = 0;"),
        "strata_hip.h::映射": open(hip, encoding="utf-8").read().count("#define cudaStreamCreateWithPriority"),
    }
    for k, v in got.items():
        print("  %-28s %d" % (k, v))
    return all(v == 1 for v in got.values())


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    tree = sys.argv[1].rstrip("/")
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    if mode == "--check":
        ok = check(tree)
        print("VERDICT:", "全在" if ok else "不完整")
        return 0 if ok else 1
    cu = os.path.join(tree, "src/prefill/gemm.cu")
    hpp = os.path.join(tree, "include/strata/prefill/gemm.hpp")
    hip = os.path.join(tree, "include/strata/platform/hip_compat/strata_hip.h")
    total = 0
    total += edit(cu, [(CU_INC_ANCHOR, CU_INC_ANCHOR + '#include "strata/kernels/native_mmvq.hpp"\n')], "#4158 include")
    total += edit(cu, [(CU_DTOR_ANCHOR, CU_DTOR_ANCHOR + "    if (mmvq_buf_) cudaFree(mmvq_buf_);\n")], "#4158 dtor")
    total += edit(cu, [(CU_GUARD_OLD, CU_GUARD_NEW)], "#4158 guard")
    total += edit(cu, [(CU_NATIVE_SIG, IMPL + CU_NATIVE_SIG)], "#4158 impl")
    total += edit(hpp, [(HPP_DECL_ANCHOR, DECL + HPP_DECL_ANCHOR)], "#4158 decl")
    total += edit(hpp, [(HPP_MEM_ANCHOR, HPP_MEM_ANCHOR + MEMBERS)], "#4158 members")
    total += edit(hip, [(HIP_DEF_ANCHOR, HIP_DEF_NEW)], "#4156 stream priority")
    print("patched=%d" % total)
    ok = check(tree)
    print("VERDICT:", "全在" if ok else "不完整")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
