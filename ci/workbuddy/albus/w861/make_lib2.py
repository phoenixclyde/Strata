#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_make_lib2.py -- 非 lazy 布局（配合 HIPBLASLT_ENABLE_LAZY_LOAD=OFF 编出来的库）。

tensile_host.cpp:2954（lazyLoad=False 分支）找的是：
    TensileLibrary_<processor>.dat   （或 .dat.zlib）
所以只写这一个 + 代码对象，不要 Mapping（那是 lazy 分支才要的）。

输入是 gen16 已经 codegen 成功的 TensileLibrary.yaml（1 个解，63 条 v_fma_mix_f32）。
"""
import os
import shutil
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile import LibraryIO  # noqa: E402

cache, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

data = LibraryIO.read(os.path.join(cache, "TensileLibrary.yaml"), "yaml")
sols = data.get("solutions", []) if isinstance(data, dict) else []
print("solutions:", len(sols))

LibraryIO.write(os.path.join(out, "TensileLibrary_gfx906"), data, "msgpack")
print("wrote TensileLibrary_gfx906(.dat / .dat.zlib)")

for f in os.listdir(cache):
    if f.endswith(".hsaco") and "xnack-" in f:
        shutil.copy2(os.path.join(cache, f), os.path.join(out, "Kernels.so-000-gfx906.hsaco"))
        print("copied", f, "-> Kernels.so-000-gfx906.hsaco")
        break

for f in sorted(os.listdir(out)):
    print("  %-42s %d" % (f, os.path.getsize(os.path.join(out, f))))
