#!/usr/bin/env python3
"""W862: VGPR/LDS per kernel from the gfx906 object's AMD metadata, and what that allows per CU.

gfx906 (Vega 20) per CU: 65536 VGPR (64 per wave x 1024 thread-slots), 40 wavefronts max
(10 per SIMD x 4 SIMD), 64 KB LDS, 16 KB L1 vector cache.
"""
import re
import subprocess

O = "/home/albus/w862_vg/native_mmvq-hip-amdgcn-amd-amdhsa-gfx906.o"
txt = subprocess.run(["/opt/rocm/llvm/bin/llvm-readelf", "--notes", O],
                     capture_output=True, text=True).stdout

# 每个 kernel 条目以 "  - .args:" 开始；字段散在条目内
entries = txt.split("\n  - .args:")[0:]
cur, out = None, []
for e in txt.split("\n  - ")[1:]:
    if not e.startswith(".args:"):
        continue
    body = e
    m = re.search(r"\.name:\s+(\S+)", body)
    name = m.group(1) if m else "?"
    def g(k):
        mm = re.search(r"\." + k + r":\s+(\d+)", body)
        return int(mm.group(1)) if mm else -1
    out.append((name, g("vgpr_count"), g("sgpr_count"), g("group_segment_fixed_size")))
    cur = None

wave = [r for r in out if "wave_kernel" in r[0]]
print("kernels=%d  wave_kernel=%d" % (len(out), len(wave)))
print("%-58s %5s %5s %7s %6s" % ("kernel", "vgpr", "sgpr", "lds", "waves/CU"))
for n, v, s, l in wave:
    if v <= 0:
        continue
    waves = min(40, 65536 // (v * 64)) if v else 0
    lds_lim = max(0, 65536 // l) if l else 40
    print("%-58s %5d %5d %7d %6d  (lds allows %s)" % (n[:58], v, s, l, waves, lds_lim))
