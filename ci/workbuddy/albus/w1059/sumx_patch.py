#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1059/R101 probe: env-gated revert of the DS4/D2S6 block-sum form in quantize_mmq_q8_1.
#   current (#31247 form):  sum = d * float(sum_q)   (scale x sum of quantized codes)
#   STRATA_SUMX=1 (probe):  sum = sum of the raw xi floats (the pre-#31247 Sigma-x form)
# a4sim-pattern (W1057): host-side getenv -> kernel parameter; default path byte-identical.
# Scratch-only: target = build-masterp overlay copy; restored + md5-verified after build.
# NOTE (W1059): the overlay is REGENERATED at CMake configure time (strata_ggml_tq_overlay.cmake)
# -- patch AFTER the reconfigure settles (two-pass ninja), or the patch is silently wiped.
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/albus/strata166/build-masterp/ggml-tq-overlay/quantize.cu"
s = io.open(P, encoding="utf-8").read()

# 1) kernel signature gains sumx
old_sig = "        const int64_t ne0, const int ne1, const int ne2, const int n_expert_used) {"
assert s.count(old_sig) == 1, s.count(old_sig)
s = s.replace(old_sig,
              "        const int64_t ne0, const int ne1, const int ne2, const int n_expert_used, const int sumx) {")

# 2) sum region: sumx selects Sigma-x; default keeps the original expressions exactly
OLD = """    float sum = 0.0f;
    if (ds_layout != MMQ_Q8_1_DS_LAYOUT_D4) {
        int sum_q = int(q.x) + int(q.y) + int(q.z) + int(q.w);

        // Calculate sums across vals_per_sum/4 threads.
#pragma unroll
        for (int offset = vals_per_sum/8; offset > 0; offset >>= 1) {
            sum_q += __shfl_xor_sync(0xFFFFFFFF, sum_q, offset, WARP_SIZE);
        }

        sum = d * float(sum_q);
    }
"""
NEW = """    float sum = 0.0f;
    if (ds_layout != MMQ_Q8_1_DS_LAYOUT_D4) {
        // W1059/R101 probe (STRATA_SUMX): revert the block sum to Sigma-x (pre-#31247 form).
        // default path keeps sum = d * float(sum_q) byte-identical.
        if (sumx) {
            float sum_x = xi.x + xi.y + xi.z + xi.w;
#pragma unroll
            for (int offset = vals_per_sum/8; offset > 0; offset >>= 1) {
                sum_x += __shfl_xor_sync(0xFFFFFFFF, sum_x, offset, WARP_SIZE);
            }
            sum = sum_x;
        } else {
        int sum_q = int(q.x) + int(q.y) + int(q.z) + int(q.w);

        // Calculate sums across vals_per_sum/4 threads.
#pragma unroll
        for (int offset = vals_per_sum/8; offset > 0; offset >>= 1) {
            sum_q += __shfl_xor_sync(0xFFFFFFFF, sum_q, offset, WARP_SIZE);
        }

        sum = d * float(sum_q);
        }
    }
"""
assert s.count(OLD) == 1, s.count(OLD)
s = s.replace(OLD, NEW, 1)

# 3) helper before the host wrapper (host-side getenv, passed at launch)
anchor = "void quantize_mmq_q8_1_cuda(\n        const float * x, const int32_t * ids, void * vy, const ggml_type type_src0,"
assert s.count(anchor) == 1
helper = """// W1059/R101 probe hook
static int strata_sumx() {
    static int v = -1;
    if (v < 0) {
        const char * e = std::getenv("STRATA_SUMX");
        v = (e && std::atoi(e) == 1) ? 1 : 0;
    }
    return v;
}

"""
s = s.replace(anchor, helper + anchor, 1)

# 4) pass the flag at the quantize_mmq_q8_1 launch sites ONLY (nvfp4/mxfp4 share the arg
#    pattern -- those kernels have no sumx parameter, never touch them; W1057 a4sim lesson)
for lay in ("D4", "DS4", "D2S6"):
    old = ("            quantize_mmq_q8_1<MMQ_Q8_1_DS_LAYOUT_%s, false>\n"
           "                <<<num_blocks, block_size, 0, stream>>>(x, ids, vy, ne00, s01, s02, s03, ne0, ne1, ne2, /*n_expert_used=*/0);") % lay
    new = ("            quantize_mmq_q8_1<MMQ_Q8_1_DS_LAYOUT_%s, false>\n"
           "                <<<num_blocks, block_size, 0, stream>>>(x, ids, vy, ne00, s01, s02, s03, ne0, ne1, ne2, /*n_expert_used=*/0, strata_sumx());") % lay
    assert s.count(old) == 1, (lay, s.count(old))
    s = s.replace(old, new)
sc_old = "                x, ids_src1_inv, vy, ne00, /*s01=*/0, /*s02=*/stride_token, /*s03=*/0, ne0, /*ne1=*/(int) nrows_dst, /*ne2=*/1, n_expert_used);"
n2 = s.count(sc_old)
assert n2 == 3, n2
s = s.replace(sc_old,
              "                x, ids_src1_inv, vy, ne00, /*s01=*/0, /*s02=*/stride_token, /*s03=*/0, ne0, /*ne1=*/(int) nrows_dst, /*ne2=*/1, n_expert_used, strata_sumx());")

if "#include <cstdlib>" not in s and "#include <stdlib.h>" not in s:
    i = s.find("#include")
    line_end = s.find("\n", i)
    s = s[:line_end + 1] + "#include <cstdlib>\n" + s[line_end + 1:]

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("PATCHED", P)
print("checks: sumx_sig=%d helper=%d launches=%d" % (
    s.count("const int n_expert_used, const int sumx) {"),
    s.count("strata_sumx() {"),
    s.count("strata_sumx());")))
