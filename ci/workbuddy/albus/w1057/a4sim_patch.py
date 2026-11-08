#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1057/R74 probe: env-gated int4 activation simulation in quantize_mmq_q8_1.
# Target = build-masterp/ggml-tq-overlay/quantize.cu (the scratch copy the build compiles).
# STRATA_A4_SIM=1 -> quantize activations to signed int4 (scale amax/7, codes in [-8,7])
# stored in the Q8_1 int8 container, so the MMQ compute path is untouched and the GEMM
# carries exactly the W4A4 activation quantization error. a4==0 keeps byte-identical math.
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/build-masterp/ggml-tq-overlay/quantize.cu"
s = io.open(P, encoding="utf-8").read()

# 1) kernel signature gains a4
old_sig = "        const int64_t ne0, const int ne1, const int ne2, const int n_expert_used) {"
assert s.count(old_sig) == 1, s.count(old_sig)
s = s.replace(old_sig,
              "        const int64_t ne0, const int ne1, const int ne2, const int n_expert_used, const int a4) {")

# 2) quantization math: a4 selects int4 levels; a4==0 preserves original expressions exactly
old_math = """    const float d_inv = 127.0f / amax;
    char4 q;
    q.x = roundf(xi.x*d_inv);
    q.y = roundf(xi.y*d_inv);
    q.z = roundf(xi.z*d_inv);
    q.w = roundf(xi.w*d_inv);
    const float d = 1.0f / d_inv;
"""
assert s.count(old_math) == 1, s.count(old_math)
new_math = """    // W1057/R74 probe hook (STRATA_A4_SIM): int4 activation simulation.
    // a4: scale = amax/7, codes clamped to [-8,7] (signed int4) in the int8 container;
    // the downstream MMQ kernel is untouched, so the GEMM output carries exactly the
    // int4 activation quantization error. a4==0 keeps the original Q8_1 expressions.
    float d, d_inv;
    if (a4) {
        d_inv = amax > 0.0f ? 7.0f / amax : 0.0f;
        d     = amax > 0.0f ? amax / 7.0f : 0.0f;
    } else {
        d_inv = 127.0f / amax;
        d     = 1.0f / d_inv;
    }
    char4 q;
    q.x = roundf(xi.x*d_inv);
    q.y = roundf(xi.y*d_inv);
    q.z = roundf(xi.z*d_inv);
    q.w = roundf(xi.w*d_inv);
    if (a4) {
        q.x = (char) fminf(7.0f, fmaxf(-8.0f, (float) q.x));
        q.y = (char) fminf(7.0f, fmaxf(-8.0f, (float) q.y));
        q.z = (char) fminf(7.0f, fmaxf(-8.0f, (float) q.z));
        q.w = (char) fminf(7.0f, fmaxf(-8.0f, (float) q.w));
    }
"""
s = s.replace(old_math, new_math)

# 3) helper before the host wrapper
anchor = "void quantize_mmq_q8_1_cuda(\n        const float * x, const int32_t * ids, void * vy, const ggml_type type_src0,"
assert s.count(anchor) == 1
helper = """// W1057/R74 probe hook
static int strata_a4_sim() {
    static int v = -1;
    if (v < 0) {
        const char * e = std::getenv("STRATA_A4_SIM");
        v = (e && std::atoi(e) == 1) ? 1 : 0;
    }
    return v;
}

"""
s = s.replace(anchor, helper + anchor)

# 4) pass the flag at the 6 quantize_mmq_q8_1 launch sites ONLY (nvfp4/mxfp4 share the
#    arg pattern -- those kernels have no a4 parameter, never touch them)
for lay in ("D4", "DS4", "D2S6"):
    old = ("            quantize_mmq_q8_1<MMQ_Q8_1_DS_LAYOUT_%s, false>\n"
           "                <<<num_blocks, block_size, 0, stream>>>(x, ids, vy, ne00, s01, s02, s03, ne0, ne1, ne2, /*n_expert_used=*/0);") % lay
    new = ("            quantize_mmq_q8_1<MMQ_Q8_1_DS_LAYOUT_%s, false>\n"
           "                <<<num_blocks, block_size, 0, stream>>>(x, ids, vy, ne00, s01, s02, s03, ne0, ne1, ne2, /*n_expert_used=*/0, strata_a4_sim());") % lay
    assert s.count(old) == 1, (lay, s.count(old))
    s = s.replace(old, new)
sc_old = "                x, ids_src1_inv, vy, ne00, /*s01=*/0, /*s02=*/stride_token, /*s03=*/0, ne0, /*ne1=*/(int) nrows_dst, /*ne2=*/1, n_expert_used);"
assert s.count(sc_old) == 3, s.count(sc_old)
s = s.replace(sc_old,
              "                x, ids_src1_inv, vy, ne00, /*s01=*/0, /*s02=*/stride_token, /*s03=*/0, ne0, /*ne1=*/(int) nrows_dst, /*ne2=*/1, n_expert_used, strata_a4_sim());")

# 5) std::getenv/atoi need <cstdlib>; add it if missing
if "#include <cstdlib>" not in s and "#include <stdlib.h>" not in s:
    i = s.find("#include")
    assert i >= 0
    line_end = s.find("\n", i)
    s = s[:line_end + 1] + "#include <cstdlib>\n" + s[line_end + 1:]

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("PATCHED", P)
print("checks: a4 sig=%d, helper=%d, launches=%d" % (
    s.count("const int n_expert_used, const int a4)"),
    s.count("strata_a4_sim() {"),
    s.count("strata_a4_sim());")))
