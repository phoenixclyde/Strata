#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Document where the two dot cores actually live.

Deliberately does NOT include gfx906_dot.hpp here: dp4a.hpp is pulled into
host-only translation units with no CUDA/HIP runtime in scope, and adding the
include broke 6 TUs on the first W1042 build (unknown __forceinline__).
"""
import pathlib

P = pathlib.Path("/home/albus/strata166/pr/k10/include/strata/kernels/dp4a.hpp")
s = P.read_text()
assert "gfx906_dot.hpp" not in s
s = s.rstrip("\n") + (
    "\n\n// W1042: the gfx906 dot4/dot8 cores.\n"
    "//   LIVE  : include/strata/platform/hip_compat/strata_hip.h defines\n"
    "//           strata_dp4a/__dp4a (v_dot4_i32_i8) and strata_dp8a/__dp8a\n"
    "//           (v_dot8_i32_i4).  STRATA_DP4A reaches the former directly;\n"
    "//           the ISA of qsa_decode_attn.cu.o shows 384 v_dot4_i32_i8.\n"
    "//   STANDALONE: include/strata/kernels/gfx906_dot.hpp carries both cores\n"
    "//           with a bit-exact scalar fallback; include it explicitly in\n"
    "//           the TU that consumes them (this header is host-visible).\n"
    "//   LEGACY: include/strata/hip_compat/intrinsics.hpp is NOT in any\n"
    "//           production depfile -- editing it alone is a no-op.\n"
    "// dot8 has no production call site yet: k8v4 keeps V as 4-bit codes but\n"
    "// attention probabilities are float, so using it needs a p->int4\n"
    "// quantiser and its own numeric gate (PORT_PLAN C2, R108).  Runtime proof\n"
    "// is tools/gfx906_dot48_selfcheck.cu.\n")
P.write_text(s)
print("dp4a.hpp: core locations + the dead-header trap documented")
