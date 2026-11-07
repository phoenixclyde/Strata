#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert8.py -- 旧 9 元素 logic -> TCL 可消费的完整 state（第五处补齐）。

累计五处，全部有源码依据，不猜：
  1) 顶层 9 -> 12 元素（[9] TileSelection / [10] PerfMetric / [11] distance）
  2) 展开 YAML 锚点（AliasEvent 让 CustomYamlLoader 状态机错位）
  3) Solution: EnableMatrixInstruction=False（gfx906 无 MFMA/WMMA）
  4) Solution: NoReject=True（reject() 第一行认这个键）
  5) ProblemType 37 -> 90 键（`ProblemType(...)` 没有 defaultSolution 兜底）
  6) **剔除已废弃的 Assert* 键**：Contractions.py::ProblemPredicate.FromOriginalKeyPair
     只接受 AssertAIGreaterThanEqual / AssertAILessThanEqual / 三个 *Multiple，
     其余 Assert* 直接 RuntimeError（旧的 AssertMinApproxSize 就死在这）
"""
import sys
import yaml

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile.SolutionStructs.Problem import ProblemType  # noqa: E402

KEEP_ASSERT = {
    "AssertAIGreaterThanEqual", "AssertAILessThanEqual",
    "AssertFree0ElementMultiple", "AssertFree1ElementMultiple",
    "AssertSummationElementMultiple",
}


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def plain(v):
    if isinstance(v, (str, bool, int, float)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    return str(v)


src, dst, dist = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "Euclidean")

TEMPLATE = ProblemType({
    "OperationType": "GEMM", "DataType": "Half", "DestDataType": "Half",
    "ComputeDataType": "Float", "HighPrecisionAccumulate": True,
    "IndexAssignmentsA": [0, 3, 2], "IndexAssignmentsB": [1, 3, 2],
    "NumIndicesC": 3, "UseBeta": True, "Batched": True,
}, False)
TEMPLATE = plain(TEMPLATE.state)

d = yaml.safe_load(open(src, encoding="utf-8"))
while len(d) < 12:
    d.append(None)
d[9] = None
d[10] = None
d[11] = dist

pt = d[4]
n_pt = 0
for k, v in TEMPLATE.items():
    if k not in pt:
        pt[k] = v
        n_pt += 1

dropped = {}
for s in d[5]:
    if not isinstance(s, dict):
        continue
    s["EnableMatrixInstruction"] = False
    s["NoReject"] = True
    for k in list(s.keys()):
        if k.startswith("Assert") and k not in KEEP_ASSERT:
            del s[k]
            dropped[k] = dropped.get(k, 0) + 1

print("ProblemType +%d 键 -> %d" % (n_pt, len(pt)))
print("Solution 剔除废弃 Assert:", dropped)
print("solutions:", len(d[5]))

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
