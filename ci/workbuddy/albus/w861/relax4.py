#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_relax4.py -- 把 benchmark 格式的 solution 转成**运行时库格式**。

TENSILE_DB 直接给了合法键表：
    taskPredicate, problemType, name, kernelName, internalArgsSupport, libraryLogicIndex,
    index, sizeMapping, problemPredicate, ideals, linearModel, debugKernel
gen16 那份（TCL benchmark 阶段产物）带的是 hardwarePredicate（非法），缺
taskPredicate / problemType / sizeMapping（必需）。所以之前 algos 永远是 0 —— 不是 predicate
匹配的问题，是 solution 根本没解析成功。

这里做最小补齐：
  - 删 hardwarePredicate（benchmark 专有，运行时不认）
  - 补 taskPredicate = {"type":"True"}（没有 task 维度的约束）
  - 补 problemType = 库顶层的 ProblemType
  - 补 sizeMapping = []  （空的 size 映射，即不按尺寸特化）
"""
import os
import shutil
import sys

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile import LibraryIO  # noqa: E402

ALLOWED = {"taskPredicate", "problemType", "name", "kernelName", "internalArgsSupport",
           "libraryLogicIndex", "index", "sizeMapping", "problemPredicate",
           "ideals", "linearModel", "debugKernel"}

cache, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

data = LibraryIO.read(os.path.join(cache, "TensileLibrary.yaml"), "yaml")
sols = data.get("solutions", [])
print("solutions:", len(sols))
if sols:
    print("orig keys:", sorted(sols[0].keys()))

# 库顶层没有 ProblemType（benchmark 产物），用解里自带的 predicate 描述不了，
# 这里从 gfx950 的运行时库里取一个同类型的 ProblemType 模板。
NEW = ("/src/projects/hipblaslt/library/src/amd_detail/rocblaslt/src/Tensile/"
       "Logic/asm_full/gfx950/gfx950/Equality/"
       "gfx950_Cijk_Ailk_Bjlk_HHS_BH_BiasSH_HAS_SAV_UserArgs.yaml")
try:
    import yaml as _y
    tmpl = _y.safe_load(open(NEW, encoding="utf-8"))
    PT = tmpl.get("ProblemType", {})
    print("ProblemType template keys:", len(PT))
except Exception as e:  # noqa
    print("template load failed:", e)
    PT = {}

for s in sols:
    # 只删非法键；其余（taskPredicate / problemType / sizeMapping）库里本来就有，
    # 替换掉反而弄坏加载。
    s.pop("hardwarePredicate", None)
    # 只留合法键，防止再来一个 Unknown key
    for k in list(s.keys()):
        if k not in ALLOWED:
            print("  drop unknown key:", k)
            del s[k]

print("after keys:", sorted(sols[0].keys()) if sols else [])

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
