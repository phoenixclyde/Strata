#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_make_lib.py -- 把 codegen 出来的 TensileLibrary.yaml 转成 hipBLASLt 运行时
(tensile_host.cpp) 真正会去找的那几个文件：

  TensileLibrary_lazy_gfx906.dat                      主库（msgpack）
  TensileLiteLibrary_lazy_gfx906_Mapping.dat          索引 {idx: kernelName_gfx906}
  Kernels.so-000-gfx906.hsaco                         代码对象（去掉 xnack 后缀）

命名依据 tensile_host.cpp:2945（lazy + !enableYaml -> TensileLibrary_lazy_<proc>.dat）
与 Run.py:1240（lazy 索引 -> TensileLiteLibrary_lazy_<arch>_Mapping）。
"""
import os
import shutil
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile import LibraryIO  # noqa: E402

cache, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

src_yaml = os.path.join(cache, "TensileLibrary.yaml")
data = LibraryIO.read(src_yaml, "yaml")
print("library keys:", list(data.keys()) if isinstance(data, dict) else type(data))
sols = data.get("solutions", []) if isinstance(data, dict) else []
print("solutions:", len(sols))

# 1) 主库
LibraryIO.write(os.path.join(out, "TensileLibrary_lazy_gfx906"), data, "msgpack")
print("wrote TensileLibrary_lazy_gfx906.dat")

# 2) 索引：{solution index: 库名_gfx906}
mapping = {}
for s in sols:
    idx = s.get("index", 0)
    name = s.get("name") or s.get("kernelName") or "lib%d" % idx
    mapping[idx] = "%s_gfx906" % name
LibraryIO.write(os.path.join(out, "TensileLiteLibrary_lazy_gfx906_Mapping"), mapping, "msgpack")
print("wrote Mapping.dat entries=%d" % len(mapping))
for k, v in list(mapping.items())[:2]:
    print("   ", k, "->", v[:80], "...")

# 3) 代码对象：去掉 xnack 后缀
for f in os.listdir(cache):
    if f.endswith(".hsaco") and "xnack-" in f:
        shutil.copy2(os.path.join(cache, f), os.path.join(out, "Kernels.so-000-gfx906.hsaco"))
        print("copied", f, "-> Kernels.so-000-gfx906.hsaco")
        break

for f in sorted(os.listdir(out)):
    print("  %-46s %d" % (f, os.path.getsize(os.path.join(out, f))))
