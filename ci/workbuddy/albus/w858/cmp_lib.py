# -*- coding: utf-8 -*-
"""对比"我们自建的 gfx906 Tensile 库"与"镜像自带的 gfx942 库"的 msgpack 键集与版本字段。"""
import glob
import os
import sys
import zlib

import msgpack


def load(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    if raw[:1] == b"\x78":
        raw = zlib.decompress(raw)
    return msgpack.unpackb(raw, raw=False, strict_map_key=False)


ours = sys.argv[1] if len(sys.argv) > 1 else ""
cands = (glob.glob("/opt/rocm/lib/hipblaslt/library/TensileLibrary_lazy_gfx942*.dat*")
         + glob.glob("/opt/rocm/lib/rocblas/library/TensileLibrary_lazy_gfx942*.dat*")
         + glob.glob("/opt/rocm/lib/*/library/TensileLibrary_lazy_gfx942*.dat*"))
print("installed candidates:", cands[:3])

files = [("ours", ours)]
for c in cands[:1]:
    files.append(("installed", c))

for tag, p in files:
    if not p:
        continue
    try:
        d = load(p)
    except Exception as e:  # noqa: BLE001
        print("==", tag, "FAIL", type(e).__name__, str(e)[:150])
        continue
    print("== ", tag, os.path.basename(p))
    print("    keys:", sorted(d.keys()))
    for k in ("version", "Version", "MinimumRequiredVersion", "Architecture",
              "KernelNames", "SolutionNames", "PackedSolutionNames",
              "TensileLiteVersion", "LibraryType"):
        if k in d:
            v = d[k]
            print("    %-24s = %s" % (k, str(v)[:140]))
