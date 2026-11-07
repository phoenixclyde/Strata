# -*- coding: utf-8 -*-
"""把我们的 lazy .dat 去掉 'version' 键（对齐 rocBLAS 自带 gfx906 库的键集），写到一个新目录里试装。"""
import os
import shutil
import sys

import msgpack

src_dir = "/out/gen5/library/gfx906"
dst_dir = "/out/gen6"
os.makedirs(dst_dir, exist_ok=True)

for name in os.listdir(src_dir):
    shutil.copy2(os.path.join(src_dir, name), os.path.join(dst_dir, name))

p = os.path.join(dst_dir, "TensileLibrary_lazy_gfx906.dat")
with open(p, "rb") as fh:
    d = msgpack.unpackb(fh.read(), raw=False, strict_map_key=False)
print("before keys:", sorted(d.keys()), "version=", d.get("version"))
d.pop("version", None)
with open(p, "wb") as fh:
    fh.write(msgpack.packb(d, use_bin_type=True))
print("after  keys:", sorted(d.keys()))
print("library entries:", list(d.get("library", {}).keys())[:3])
