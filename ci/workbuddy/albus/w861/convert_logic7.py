#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert7.py -- 旧 9 元素 logic -> TCL 可消费的完整 state。

四处补齐，全部用**引擎自己的默认值**，不猜：
  1) 顶层 9 -> 12 元素（[9] TileSelection, [10] PerfMetric, [11] distance）
  2) 展开 YAML 锚点（AliasEvent 会让 CustomYamlLoader 状态机错位）
  3) 每个 Solution: EnableMatrixInstruction=False（gfx906 无 MFMA/WMMA）+ NoReject=True
     （reject() 第一行就认这个键，见 Utilities.py；与 W858 §11.3 的 NoReject 同一机制）
  4) **ProblemType 从 37 键补到 90 键**：旧 rocBLAS logic 没有
     ActivationComputeDataType / MXBlock* / IndexAssignmentsLD / MetadataLayout 这一族，
     而 `ProblemType(...)` 构造时不像 Solution 那样有 defaultSolution 兜底 -> KeyError。
     这里用一个最小 HHS 描述构造 ProblemType，取它的 state 当模板。
"""
import sys
import yaml

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile.SolutionStructs.Problem import ProblemType  # noqa: E402


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def plain(v):
    """ProblemType.state 里的数据类型是 rocisa 枚举（如 H），YAML 不能直接写。"""
    if isinstance(v, (str, bool, int, float)) or v is None:
        return v
    if isinstance(v, list):
        return [plain(x) for x in v]
    if isinstance(v, tuple):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    return str(v)


src, dst, dist = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "Euclidean")

# 模板：最小 HHS，让引擎把 90 个键自己填出来
TEMPLATE = ProblemType({
    "OperationType": "GEMM", "DataType": "Half", "DestDataType": "Half",
    "ComputeDataType": "Float", "HighPrecisionAccumulate": True,
    "IndexAssignmentsA": [0, 3, 2], "IndexAssignmentsB": [1, 3, 2],
    "NumIndicesC": 3, "UseBeta": True, "Batched": True,
}, False)
TEMPLATE = plain(TEMPLATE.state)

d = yaml.safe_load(open(src, encoding="utf-8"))
print("top len before:", len(d))
while len(d) < 12:
    d.append(None)
d[9] = None
d[10] = None
d[11] = dist

# --- ProblemType 补全 ---
pt = d[4]
pt_add = {}
for k, v in TEMPLATE.items():
    if k not in pt:
        pt[k] = v
        pt_add[k] = v
print("ProblemType: %d -> %d 键，补了 %d 个" % (len(pt) - len(pt_add), len(pt), len(pt_add)))
for k in sorted(pt_add)[:12]:
    print("    + %-36s = %r" % (k, pt_add[k]))

# --- Solution 补全 ---
sol_add = {}
for s in d[5]:
    if not isinstance(s, dict):
        continue
    for k, v in {"EnableMatrixInstruction": False, "NoReject": True}.items():
        if s.get(k) != v:
            s[k] = v
            sol_add[k] = sol_add.get(k, 0) + 1
print("solutions:", len(d[5]), " 设置:", sol_add)

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
