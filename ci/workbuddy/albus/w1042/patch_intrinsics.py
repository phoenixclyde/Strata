#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: align the LEGACY intrinsics.hpp with the live compat header.

This header is NOT in any production compile chain (verified: no .d depfile
mentions it; the live __dp4a is strata_hip.h::strata_dp4a).  The first W1042
attempt patched only this file and produced a byte-identical binary -- a
"changed the wrong object" trap.  We still add the A0 gfx906 branch so the two
copies do not diverge, and, more importantly, put a warning at the top so the
next person does not repeat the mistake.
"""
import pathlib

K10 = pathlib.Path("/home/albus/strata166/pr/k10/include/strata/hip_compat/intrinsics.hpp")
PA = pathlib.Path("/home/albus/strata166/pr/port-all/include/strata/hip_compat/intrinsics.hpp")

WARNING = (
    "// W1042 WARNING: this header is NOT in the production compile chain.\n"
    "// The live HIP compat layer is include/strata/platform/hip_compat/strata_hip.h\n"
    "// (it defines strata_dp4a / __dp4a and, since W1042, strata_dp8a / __dp8a).\n"
    "// No .d depfile in build-masterp references this file.  Editing it alone\n"
    "// changes nothing in the binary -- verify the depfile before treating a\n"
    "// change here as an optimisation.  Kept in sync to avoid drift.\n"
)

src = PA.read_text().splitlines(True)
block = "".join(src[25:32])                      # 1-based lines 26..32 = the A0 #elif
assert block.startswith("#elif (defined(__gfx906__)"), repr(block[:80])
assert "__builtin_amdgcn_sdot4(a, b, c, false)" in block
assert block.count("\n") == 7, block.count("\n")

s = K10.read_text()
assert "__gfx906__" not in s, "gfx906 branch already present - do not double-insert"
assert "W1042 WARNING" not in s
anchor = "#elif (defined(__gfx1030__)"
assert s.count(anchor) == 1, s.count(anchor)
s = WARNING + s
s = s.replace(anchor, block + anchor)
K10.write_text(s)
print("intrinsics.hpp: dead-header warning + A0 gfx906 dot4 branch (%d lines)" % block.count("\n"))
