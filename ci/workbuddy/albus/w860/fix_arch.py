# -*- coding: utf-8 -*-
"""fix_arch.py -- 把 gfx906 加回 TensileLite 的架构白名单。

踩过两次：`tensilelite_supported_architectures.cmake` 里没有 gfx906，于是
- TensileCreateLibrary 的 `Architectures to process` 为空；
- Tensile / client 的 CMake 直接 `tensilelite_validate_gpu_targets` FATAL。
"""
import io
import re
import sys

P = sys.argv[1] if len(sys.argv) > 1 else (
    "/src/projects/hipblaslt/cmake/tensilelite_supported_architectures.cmake"
)
s = io.open(P, encoding="utf-8").read()
if '"gfx906"' in s or "'gfx906'" in s or "gfx906;" in s:
    print("  already has gfx906")
    sys.exit(0)

m = re.search(r"set\(SUPPORTED_ARCHITECTURES([^\)]*)\)", s, re.S)
if not m:
    print("  !! SUPPORTED_ARCHITECTURES not found")
    sys.exit(1)
inner = m.group(1)
new_inner = inner.rstrip()
sep = "" if new_inner.endswith("\n") else "\n"
new_inner = new_inner + sep + "  gfx906\n"
s = s[:m.start(1)] + new_inner + s[m.end(1):]
io.open(P, "w", encoding="utf-8").write(s)
print("  gfx906 added to SUPPORTED_ARCHITECTURES")
