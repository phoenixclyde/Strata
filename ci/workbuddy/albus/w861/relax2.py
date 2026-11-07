#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_relax2.py -- 从 yaml 读库、放宽 predicate、直接写成 lazy 主库 + 子库 + mapping。

为什么放宽：gen16 的 predicate 是 benchmark 针对单一 problem size 生成的，
带 WorkgroupNumberCheck[128,32,1] 等硬约束。生产形状 M=256 N=5120 K=2560 数学上满足却仍
algos=0，所以做一次"最松 predicate"的对照实验：
  - 若 algos 变 >0 -> 库/solution/kernel 都好，问题只在 predicate 匹配
  - 若仍为 0    -> solution 自身不可用（kernel 参数与 gfx906 不符）
"""
import os
import shutil
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile import LibraryIO  # noqa: E402

cache, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

data = LibraryIO.read(os.path.join(cache, "TensileLibrary.yaml"), "yaml")
sols = data.get("solutions", [])
print("solutions:", len(sols))

MINIMAL = {"type": "And", "value": [
    {"type": "OperationIdentifierEqual", "value": "Contraction_l_Ailk_Bjlk_Cijk_Dijk"},
    {"type": "TypesEqual", "value": ["Half", "Half", "Half", "Half", "Half", "Half"]},
    {"type": "HighPrecisionAccumulate", "value": True},
    {"type": "UseBias", "value": 0},
]}

n = 0
for s in sols:
    if "problemPredicate" in s:
        s["problemPredicate"] = MINIMAL
        n += 1
if isinstance(data.get("library"), dict):
    for row in data["library"].get("rows", []):
        if "predicate" in row:
            row["predicate"] = MINIMAL
            n += 1
print("predicates relaxed:", n)

LibraryIO.write(os.path.join(out, "TensileLibrary_lazy_gfx906"), data, "msgpack")
LibraryIO.write(os.path.join(out, "TensileLibrary_lazy_gfx906_gfx906"), data, "msgpack")
mapping = {int(s.get("index", 0)): "TensileLibrary_lazy_gfx906_gfx906" for s in sols}
LibraryIO.write(os.path.join(out, "TensileLiteLibrary_lazy_gfx906_Mapping"), mapping, "msgpack")
print("mapping:", mapping)

for f in os.listdir(cache):
    if f.endswith(".hsaco") and "xnack-" in f:
        shutil.copy2(os.path.join(cache, f), os.path.join(out, "Kernels.so-000-gfx906.hsaco"))
        break

for f in sorted(os.listdir(out)):
    print("  %-50s %d" % (f, os.path.getsize(os.path.join(out, f))))
