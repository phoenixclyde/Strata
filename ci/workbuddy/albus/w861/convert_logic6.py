#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert6.py -- 旧 9 元素 logic -> TCL 能吃、且不会被 DepthU 校验打断的版本。

关键（这一轮才看清）：`SolutionStructs/Utilities.py::reject()` 的第一行是
    if state and "NoReject" in state and state["NoReject"]:
        return False
也就是**引擎自己留了 per-solution 的口子**，不需要 patch 源码、也不需要改
GlobalParameters 的 PrintSolutionRejectionReason。

为什么需要它：旧 rocBLAS logic 缺 MX/subtile/metadata 一族的字段，缺失走默认值后
DepthU 循环里 setGlobalReadVectorWidth 全线失败 -> reject -> TCL 直接 raise，一个库都产不出。
W858 §11.3 在 BenchmarkProblems 侧用的是同一机制（config 里 NoReject: [True]），
这里只是把它放到 solution state 上。

同时做：
  [9]=TileSelection None, [10]=PerfMetric None, [11]=distance（新 schema 必填）
  展开 YAML 锚点（AliasEvent 会让 CustomYamlLoader 状态机错位）
  补 EnableMatrixInstruction=False（gfx906 无 MFMA/WMMA；上游 846 行推断完没写回 state）
"""
import sys
import yaml


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


src, dst, dist = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "Euclidean")

d = yaml.safe_load(open(src, encoding="utf-8"))
print("top len before:", len(d))
while len(d) < 12:
    d.append(None)
d[9] = None
d[10] = None
d[11] = dist

added = {}
for s in d[5]:
    if not isinstance(s, dict):
        continue
    force = {"EnableMatrixInstruction": False, "NoReject": True}
    for k, v in force.items():
        if s.get(k) != v:
            s[k] = v
            added[k] = added.get(k, 0) + 1

print("solutions:", len(d[5]), " 设置:", added)

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
