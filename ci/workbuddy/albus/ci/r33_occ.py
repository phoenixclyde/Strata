# -*- coding: utf-8 -*-
"""[W863 R33] Occupancy of the HC kernel family, computed from the shipped device assembly.

gfx906 (Vega 20 / MI50), from AMD's published model:
  * 256 VGPR (32-bit) per SIMD; allocation granule 4
  * 4 SIMDs per CU; 64 KiB LDS per CU; max 40 waves per CU (10 per SIMD)
  * a workgroup of THREADS=256 is 4 wave64s
So:
  waves_per_simd = min(10, 256 // roundup4(vgpr))
  waves_cu_vgpr  = 4 * waves_per_simd
  blocks_cu_lds  = 65536 // lds_per_block
  blocks_cu      = min(waves_cu_vgpr // 4, blocks_cu_lds)
  occupancy      = blocks_cu * 4 waves * 64 threads / 2048 threads-per-CU
"""
import re

S = "/home/albus/strata166/ci/state/vgpr/fused_gr.s"
txt = open(S, errors="replace").read()

def waves_per_simd(vgpr):
    g = ((vgpr + 3) // 4) * 4
    return max(1, min(10, 256 // g))

kernels = {}
for m in re.finditer(r"\n\s*\.amdhsa_kernel\s+(\S+)(.*?)(?=\n\s*\.amdhsa_kernel\s|\Z)", txt, re.S):
    name, body = m.group(1), m.group(2)
    def fld(k, d=-1):
        mm = re.search(r"\.%s\s+(\d+)" % k, body)
        return int(mm.group(1)) if mm else d
    vgpr = fld("amdhsa_next_free_vgpr")
    if vgpr < 0:
        continue
    kernels[name] = dict(vgpr=vgpr, sgpr=fld("amdhsa_next_free_sgpr"),
                         lds=fld("amdhsa_group_segment_fixed_size", 0),
                         priv=fld("amdhsa_private_segment_fixed_size", 0))

def T_of(name):
    m = re.search(r"gr_(down|up)_q8_(fast_)?kernelILi(\d+)E", name)
    return (m.group(1), bool(m.group(2)), int(m.group(3))) if m else None

rows = []
for name, k in kernels.items():
    t = T_of(name)
    if not t:
        continue
    kind, fast, T = t
    w = waves_per_simd(k["vgpr"])
    waves_cu_vgpr = 4 * w
    blocks_lds = 65536 // k["lds"] if k["lds"] else 10
    blocks = min(waves_cu_vgpr // 4, blocks_lds)
    rows.append((kind, fast, T, k["vgpr"], k["lds"], blocks,
                 100.0 * blocks * 256 / 2048.0))

print("HC q8 kernels: occupancy by template parameter T (the verification window size)")
print()
print("%-6s %-5s %3s %6s %8s %8s %9s %9s" %
      ("kernel", "fast", "T", "vgpr", "lds/blk", "blk/CU", "thr/CU", "occupancy"))
print("-" * 62)
for kind in ("down", "up"):
    for T in range(1, 9):
        for fast in (False, True):
            hit = [r for r in rows if r[0] == kind and r[1] is fast and r[2] == T]
            if not hit:
                continue
            _, _, _, vgpr, lds, blocks, occ = hit[0]
            print("%-6s %-5s %3d %6d %8d %8d %9d %8.1f%%" %
                  (kind, "yes" if fast else "no", T, vgpr, lds, blocks, blocks * 256, occ))
    print()

print("读法：")
print("  * T 是验证窗口的列数（生产典型 T=2，--spec 4 上限 4）")
print("  * 占用率 = 每 CU 常驻线程 / 2048；gfx906 每 SIMD 只有 256 个 VGPR，是硬上限")
print("  * 256 VGPR × 4 SIMD / (每线程 VGPR) = 每 CU 的线程上限")
