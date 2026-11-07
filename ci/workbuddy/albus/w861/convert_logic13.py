#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert13.py -- **以别的架构的 solution 为骨架**（这是本条线的正解）。

前面 12 轮都是在"旧 rocBLAS logic 上逐个补缺字段"，每补一个又冒出下一个
（EnableMatrixInstruction -> ActivationComputeDataType -> AssertMinApproxSize ->
 ExpertSchedulingMode -> NumLdsBlk...）。原因是那份 logic 是 2019 年的 rocBLAS 产物，
字段集（125 键）与 2026 年的 TensileLite（161 键）不是一个时代。

正解：
    骨架 = gfx950 那份新格式 logic 的 Solutions[0]（161 键，引擎自己产出的完整字段集）
    灌入 = 旧 rocBLAS 解的实际调优参数（DepthU / MacroTile / ThreadTile / WorkGroup /
           VectorWidth / GlobalReadVectorWidth / WaveTile / UnrollMajorLDS ...）
    强制 = gfx906 约束（EnableMatrixInstruction=False、MatrixInstruction=[]、
           WavefrontSize=64、KernelLanguage=Assembly、NoReject=True）
    剔除 = 旧 Assert*（Contractions.py 只认三类）
    顶层 = 13 元素，[12] 放 gfx950 的 DefaultSolution（引擎的 libDefaults 会再兜一层）

骨架保证"不缺任何字段"；灌入保证"kernel 是 gfx906 的调优参数"。
"""
import sys
import yaml

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile.Common.ValidParameters import validParameters  # noqa: E402


def _want(keys):
    """validParameters 里这个键声明的是什么 python 类型（有些键的值是单个数，要跳过）。"""
    if keys is None or not isinstance(keys, (list, tuple, set, frozenset)) or not keys:
        return None
    has_bool = any(isinstance(k, bool) for k in keys)
    has_int = any(isinstance(k, int) and not isinstance(k, bool) for k in keys)
    has_str = any(isinstance(k, str) for k in keys)
    if has_bool and not has_int:
        return bool
    if has_int and not has_bool:
        return int
    if has_str:
        return str
    return None


def coerce(k, v):
    """bool <-> int 归一。msgpack 里两者是不同 wire type，混了会 std::bad_cast。"""
    t = _want(validParameters.get(k))
    if t is int and isinstance(v, bool):
        return int(v)
    if t is bool and isinstance(v, int) and not isinstance(v, bool):
        return bool(v)
    return v

NEW = ("/src/projects/hipblaslt/library/src/amd_detail/rocblaslt/src/Tensile/"
       "Logic/asm_full/gfx950/gfx950/Equality/"
       "gfx950_Cijk_Ailk_Bjlk_HHS_BH_BiasSH_HAS_SAV_UserArgs.yaml")

KEEP_ASSERT = {
    "AssertAIGreaterThanEqual", "AssertAILessThanEqual",
    "AssertFree0ElementMultiple", "AssertFree1ElementMultiple",
    "AssertSummationElementMultiple",
}
GFX906 = {
    "EnableMatrixInstruction": False,
    "MatrixInstruction": [],
    "WavefrontSize": 64,
    "KernelLanguage": "Assembly",
    "NoReject": True,
    # KernelWriter._initKernel:7437 无条件读 kernel["NumLdsBlk"]，而 Solution.py:5522
    # 只在 MI 路径的 LDS 计算里赋值 —— non-MI 路径根本没设过（上游同款"非 MI 无测试"疏漏）。
    # PGR2 + 1LDSBuffer=0 的常规取值是 2。
    "NumLdsBlk": 2,
}
# 骨架里这些是 gfx950 的 MFMA 专属值，灌入后必须清掉，否则会污染非 MI 路径
MI_ONLY = ["MatrixInstM", "MatrixInstN", "MatrixInstK", "MatrixInstB",
           "MatrixInstBM", "MatrixInstBN", "MIWaveTile", "MIWaveGroup",
           "MIOutputVectorWidth", "MIInputPerThread", "MIArchVgpr",
           "MIBlockM", "MIFlatten", "MIAllowSparse", "MIStaggerU",
           "MIDistributed", "MILdsPad"]


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


src, dst = sys.argv[1], sys.argv[2]
tmpl = yaml.safe_load(open(NEW, encoding="utf-8"))
d = yaml.safe_load(open(src, encoding="utf-8"))

base = dict(tmpl["Solutions"][0])
print("骨架 Solutions[0]: %d 键" % len(base))

new_sols = []
for old in d[5]:
    if not isinstance(old, dict):
        continue
    s = dict(base)          # 1) 完整骨架
    s.update(old)           # 2) 旧解的真实调优参数
    s.update(GFX906)        # 3) gfx906 约束
    s.pop("ISA", None)
    for k in MI_ONLY:       # 4) 清掉 MFMA 专属
        s.pop(k, None)
    for k in list(s.keys()):
        if k.startswith("Assert") and k not in KEEP_ASSERT:
            del s[k]
    for k in list(s.keys()):     # 5) 类型归一（bool <-> int）
        s[k] = coerce(k, s[k])
    new_sols.append(s)

d[5] = new_sols
print("解数:", len(new_sols), " 每个键数:", len(new_sols[0]))

# ProblemType 补到 86 键
for k, v in tmpl["ProblemType"].items():
    if k not in d[4]:
        d[4][k] = v

ds = dict(tmpl["DefaultSolution"])
ds.update(GFX906)
ds.pop("ISA", None)
for k in list(ds.keys()):
    ds[k] = coerce(k, ds[k])

while len(d) < 13:
    d.append(None)
d[9] = None
d[10] = tmpl.get("PerfMetric")
d[11] = tmpl.get("LibraryType") or "Euclidean"
d[12] = ds

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
