#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_make_lib3.py -- lazy 布局，mapping 指回主库自身。

依据 MasterSolutionLibrary.hpp::initLibraryMapping：
    stem 必须以 "TensileLibrary_lazy_" 开头，arch = stem 去掉前缀
    libraryMapping = LoadLibraryMapping("<dir>/TensileLiteLibrary_lazy_<arch>_Mapping.dat")
    mapping 是 {solutionIndex: <库名>}，加载子库时按 <dir>/<库名><suffix> 拼路径

我们只有一个解、一个库：让 mapping 指向主库自己
    value = "TensileLibrary_lazy_gfx906"
于是它去开 <dir>/TensileLibrary_lazy_gfx906.dat —— 正是主库，solutions 就在里面。
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
print("solutions in source library:", len(sols))

# 主库：lazy 命名
LibraryIO.write(os.path.join(out, "TensileLibrary_lazy_gfx906"), data, "msgpack")
print("wrote TensileLibrary_lazy_gfx906.dat(.zlib)")

# 索引：每个解 -> 主库自身
mapping = {}
for s in sols:
    mapping[int(s.get("index", 0))] = "TensileLibrary_lazy_gfx906"
LibraryIO.write(os.path.join(out, "TensileLiteLibrary_lazy_gfx906_Mapping"), mapping, "msgpack")
print("mapping:", mapping)

# 另存一份同名子库（万一它按 <libname>_<arch> 拼）
for idx, name in mapping.items():
    sub = os.path.join(out, "%s_gfx906" % name)
    if not os.path.exists(sub + ".dat") and not os.path.exists(sub + ".dat.zlib"):
        LibraryIO.write(sub, data, "msgpack")
        print("also wrote sub-library:", os.path.basename(sub))

for f in os.listdir(cache):
    if f.endswith(".hsaco") and "xnack-" in f:
        shutil.copy2(os.path.join(cache, f), os.path.join(out, "Kernels.so-000-gfx906.hsaco"))
        print("copied", f)
        break

for f in sorted(os.listdir(out)):
    print("  %-52s %d" % (f, os.path.getsize(os.path.join(out, f))))
