# -*- coding: utf-8 -*-
"""[W788 R5-A] Make the gfx906 down-kernel tile selectable (2560 default, 1280 opt-in).

Why: on gfx906 `down_chunk()` hardcodes `small_tile = false`, i.e. TILEV 2560. At the decode batch
(T ~= 3.3 tokens) the dynamic shared memory is T*TILEV*4 = 34 KiB, and a 64 KiB LDS holds one such
block per SM. The kernel's grid is DOWN_BLOCKS+1 = 41 blocks (LR 320 / WARPS 8 + 1 inject), so on a
60-CU MI50 nineteen CUs idle and each busy CU runs 8 of its 40 warp slots (~13.6% overall). Measured
HC down+up is 7.42 ms/window against a 0.78 ms weight-read floor (W788 section 2).

TILEV 1280 halves the tile (17 KiB), so three blocks share an SM. The 1280 instantiations and the
`tv == 1280` branch already exist in launch_multi (lines ~1307-1310); only the choice was hardcoded.

Gate: STRATA_GR_TILEV=1280 opts in. Unset (or anything else) keeps 0.2.4's behaviour byte for byte.
"""
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else "/src/src/kernels/cuda/fused_gr.cu"
s = io.open(P, encoding="utf-8").read()

OLD = """#if defined(STRATA_HIP_GFX906)
        const bool small_tile = false;  // gfx906: 64 KiB LDS, the 2560 tile as before (8 tokens slice into launches)
#else"""
NEW = """#if defined(STRATA_HIP_GFX906)
        // [W788 R5-A] STRATA_GR_TILEV=1280 opts into the smaller tile: T*1280*4 = 17 KiB of dynamic shared at
        // 3.3 tokens instead of 34, so three blocks share an SM instead of one. The 41-block grid leaves 19 of
        // 60 CUs idle at 1 block/SM. Unset keeps the 2560 tile, byte for byte as in 0.2.4.
        const char* gr_tv = std::getenv("STRATA_GR_TILEV");
        const bool small_tile = gr_tv != nullptr && std::atoi(gr_tv) == 1280;
#else"""
assert s.count(OLD) == 1, "anchor count = %d" % s.count(OLD)
s = s.replace(OLD, NEW, 1)

checks = [
    ("env read", s.count('"STRATA_GR_TILEV"'), 1),
    ("gate expr", s.count("const bool small_tile = gr_tv != nullptr && std::atoi(gr_tv) == 1280;"), 1),
    ("old false gone", s.count("const bool small_tile = false;"), 0),
    ("sm75 path kept", s.count("small_tile = strata::cc_major_of"), 1),
    ("tv branch kept", s.count("} else if (tv == 1280) {"), 1),
    ("1280 launch kept", s.count("gr_down_multi_kernel<1280, 4, true><<<"), 1),
    ("2560 launch kept", s.count("gr_down_multi_kernel<2560, 4, true><<<"), 1),
]
bad = [(n, g, w) for n, g, w in checks if g != w]
assert not bad, "post-patch assertions failed: %s" % bad

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("W788 R5-A patched:", P)
for n, g, w in checks:
    print("  [OK] %-16s %d" % (n, g))
