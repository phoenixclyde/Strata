#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_relax3.py -- 同时放宽 problemPredicate 与 hardwarePredicate。

前几轮只放宽了 problemPredicate 仍 algos=0，怀疑卡在 hardwarePredicate：
gen16 里写的是 {type: AMDGPU, value: {type: Processor, value: gfx906}}，
而实际设备名是 "gfx906:sramecc+:xnack-"，sramecc/xnack 两个特性可能对不上。
这里把 hardwarePredicate 换成恒真，做一次决定性对照。
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
if sols:
    print("hardwarePredicate 原值:", sols[0].get("hardwarePredicate"))

MINIMAL = {"type": "And", "value": [
    {"type": "OperationIdentifierEqual", "value": "Contraction_l_Ailk_Bjlk_Cijk_Dijk"},
    {"type": "TypesEqual", "value": ["Half", "Half", "Half", "Half", "Half", "Half"]},
    {"type": "HighPrecisionAccumulate", "value": True},
    {"type": "UseBias", "value": 0},
]}
TRUE_PRED = {"type": "True"}

for s in sols:
    if "problemPredicate" in s:
        s["problemPredicate"] = MINIMAL
    # {"type":"True"} 不是合法 predicate（加载会失败），改为直接删除，
    # 让硬件匹配走默认路径；这能把"是不是 hardwarePredicate 筛掉的"单独验出来。
    s.pop("hardwarePredicate", None)
if isinstance(data.get("library"), dict):
    for row in data["library"].get("rows", []):
        if "predicate" in row:
            row["predicate"] = MINIMAL

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
