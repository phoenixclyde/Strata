# -*- coding: utf-8 -*-
"""[W863 R33] Parse the device assembly for every kernel's VGPR/SGPR/LDS, then compute occupancy.

gfx906 facts used (Vega 20 / MI50):
  * 256 VGPR (32-bit) per SIMD, allocation granule 4
  * 4 SIMD per CU -> 64 KiB LDS per CU
  * max 10 waves per SIMD, 40 waves per CU
So:
  waves_per_simd = min(10, 256 // roundup4(vgpr))
  blocks_per_cu  = 65536 // lds_per_block
  occupancy (threads) = min(waves_per_simd, blocks_per_cu * waves_per_block) * 64 / 2048
with waves_per_block = ceil(threads_per_block / 64); THREADS is 256 in this kernel family = 4 waves.
"""
import re, sys

S = "/home/albus/strata166/ci/state/vgpr/fused_gr.s"
txt = open(S, errors="replace").read()

THREADS = 256
WAVES_PER_BLOCK = THREADS // 64


def waves_per_simd(vgpr):
    g = ((vgpr + 3) // 4) * 4
    return max(1, min(10, 256 // g))


rows = []
# each descriptor starts at a line "	.amdhsa_kernel <name>" and lists its fields until the next one
for m in re.finditer(r"\n\s*\.amdhsa_kernel\s+(\S+)(.*?)(?=\n\s*\.amdhsa_kernel\s|\Z)", txt, re.S):
    name, body = m.group(1), m.group(2)

    def fld(k, default=-1):
        mm = re.search(r"\.%s\s+(\d+)" % k, body)
        return int(mm.group(1)) if mm else default

    vgpr = fld("amdhsa_next_free_vgpr")
    sgpr = fld("amdhsa_next_free_sgpr")
    lds = fld("amdhsa_group_segment_fixed_size", 0)
    priv = fld("amdhsa_private_segment_fixed_size", 0)
    if vgpr < 0:
        continue
    if not ("gr_" in name or "q8" in name.lower()):
        continue
    w = waves_per_simd(vgpr)
    blk_lds = 65536 // lds if lds > 0 else 99
    # a block is 4 waves; LDS caps the blocks that can be resident per CU
    blocks_per_cu = min(blk_lds, 40 // WAVES_PER_BLOCK)
    waves = min(w, blocks_per_cu * WAVES_PER_BLOCK)
    rows.append((name, vgpr, sgpr, lds, priv, w, blocks_per_cu, waves))

# de-mangle just enough to read: strip the namespace and template args noise
def short(n):
    n = re.sub(r"_ZN6strata7kernels12_GLOBAL__N_1", "", n)
    n = re.sub(r"^(\d+)", r"", n)
    n = n.replace("ENS1_7GrMultiE", "(GrMulti)").replace("EPKf", "(float*)")
    return n[:44]


print("%-46s %5s %5s %8s %8s %6s %6s %7s %7s" %
      ("kernel", "vgpr", "sgpr", "lds/blk", "priv", "w/SIMD", "blk/CU", "waves", "thr/CU%"))
print("-" * 108)
for name, vgpr, sgpr, lds, priv, w, bpc, waves in sorted(rows, key=lambda r: -r[1])[:18]:
    occ = 100.0 * waves * 64 / 2048.0
    print("%-46s %5d %5d %8d %8d %6d %6d %7d %6.0f%%" %
          (short(name), vgpr, sgpr, lds, priv, w, bpc, waves, occ))

print()
print("kernels inspected: %d" % len(rows))
hc = [r for r in rows if "q8" in r[0].lower() or "gr_down" in r[0] or "gr_up" in r[0]]
print("HC-family kernels found: %d" % len(hc))
for name, vgpr, sgpr, lds, priv, w, bpc, waves in hc[:12]:
    print("   %-44s vgpr=%-4d lds=%-6d waves/SIMD=%d  blocks/CU=%d -> %.0f%% occupancy"
          % (short(name), vgpr, lds, w, bpc, 100.0 * waves * 64 / 2048.0))
