# -*- coding: utf-8 -*-
"""0.8.0's ggml_cuda_mmq_write_back_mma gained a fifth template argument `has_fusion`; the overlay's
trellis MMA case passes four.  Append `, false` on the new signature (and nothing on the old one)."""
import io, sys

W = sys.argv[1]
p = W + "/cmake/strata_ggml_tq_overlay.cmake"
s = io.open(p, encoding="utf-8").read()
n = 0

a1 = '  set(_ps "")        # ", prec_src1" in the generated callbacks'
b1 = '  set(_ps "")        # ", prec_src1" in the generated callbacks\n  set(_pfb "")       # ", false"  in the generated write-back (0.8.0 added has_fusion)'
if "_pfb" not in s and a1 in s:
    s = s.replace(a1, b1, 1); n += 1

a2 = '''    set(_ps ", prec_src1")'''
if a2 in s and '_pfb ", false"' not in s:
    s = s.replace(a2, '''    set(_ps ", prec_src1")
    set(_pfb ", false")''', 1); n += 1

a3 = "ggml_cuda_mmq_write_back_mma<type, J, fallback${_ps}>);"
b3 = "ggml_cuda_mmq_write_back_mma<type, J, fallback${_ps}${_pfb}>);"
if a3 in s:
    s = s.replace(a3, b3, 1); n += 1

io.open(p, "w", encoding="utf-8", newline="").write(s)
print("edits:", n, "| has _pfb:", "_pfb" in s)
