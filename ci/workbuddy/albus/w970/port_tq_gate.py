# -*- coding: utf-8 -*-
"""Port the trellis overlay to 0.8.0's loader signature.

0.8.0 (#29948) gives ggml_cuda_mmq_load_tiles_t a second weight pointer `x_gate` (the fused gate/up
path).  The trellis loader (third_party/ggml-tq/tq-mmq-tiles.cuh) still has 0.4.1's five parameters,
so it no longer converts to the function-pointer type and the overlay's injected cases fail to
construct ggml_cuda_mmq_util_funcs.  Insert the parameter when the pinned tree has it, and mark it
unused (trellis has no fused path).
"""
import io, sys

W = sys.argv[1]
p = W + "/cmake/strata_ggml_tq_overlay.cmake"
s = io.open(p, encoding="utf-8").read()

anchor = '''  file(READ "${_tq}/tq-mmq-tiles.cuh" _tiles)'''
add = '''  file(READ "${_tq}/tq-mmq-tiles.cuh" _tiles)
  # 0.8.0 (b12099, #29948) gives the tile loader a second weight pointer for the fused gate/up path:
  # ggml_cuda_mmq_load_tiles_t(x, x_gate, x_tile, kbx0, i_max, stride).  The trellis loader has 0.4.1's
  # five parameters, so it stops converting to that function-pointer type and the injected cases fail to
  # construct ggml_cuda_mmq_util_funcs.  Take the parameter when the pinned tree has it and ignore it.
  string(FIND "${_m}" "ggml_cuda_mmq_load_tiles_t)(const char * __restrict__ x, const char * __restrict__ x_gate" _tq_gate)
  if(NOT _tq_gate LESS 0)
    string(REPLACE "const char * __restrict__ x, int * __restrict__ x_tile"
                   "const char * __restrict__ x, const char * __restrict__ x_gate, int * __restrict__ x_tile"
                   _tiles "${_tiles}")
  endif()'''

if "x_gate" in s:
    print("already patched")
elif anchor in s:
    s = s.replace(anchor, add, 1)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print("overlay patched for x_gate")
else:
    print("anchor MISS")
