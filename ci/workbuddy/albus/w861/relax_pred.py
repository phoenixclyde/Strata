#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_relax_pred.py -- 把库里的 problem predicate 放宽到"类型对就给解"，定位 algos=0 的成因。

gen16 那份 predicate 带 WorkgroupNumberCheck[128,32,1] / BoundSizeMultiple 等一堆约束，
是 benchmark 阶段针对单一 problem size 生成的。生产形状 M=256 N=5120 K=2560 在数学上满足，
但仍 algos=0，说明还有隐藏条件。这里先做**对照实验**：把 predicate 放到最松，
如果 algos 变 >0，就证明库/solution/kernel 都是好的，问题只在 predicate 匹配。
"""
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile import LibraryIO  # noqa: E402

src, dst = sys.argv[1], sys.argv[2]
data = LibraryIO.read(src, "msgpack")
print("keys:", list(data) if isinstance(data, dict) else type(data))
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

LibraryIO.write(dst, data, "msgpack")
print("wrote", dst)
