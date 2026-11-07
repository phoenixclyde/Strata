#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert4.py -- 旧 9 元素 logic -> 新 loader，三件事一次做完：

1) 顶层补齐到 12 元素（[9]=TileSelection, [10]=PerfMetric, [11]=distance）
2) 展开 YAML 锚点（AliasEvent 会让 CustomYamlLoader 的状态机错位）
3) 用引擎自己的 `defaultSolution` 给 128 个 Solution 补齐新 schema 缺的键
   （旧 rocBLAS logic 没有 EnableMatrixInstruction 等新字段）

第 3 步是关键：不猜默认值，直接问引擎。
"""
import sys
import yaml

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile.Common.ValidParameters import defaultSolution  # noqa: E402


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

sols = d[5]
added_hist = {}
for s in sols:
    if not isinstance(s, dict):
        continue
    for k, v in defaultSolution.items():
        if k not in s:
            s[k] = v
            added_hist[k] = added_hist.get(k, 0) + 1

print("solutions:", len(sols), " 补齐字段数:", len(added_hist))
for k, n in sorted(added_hist.items(), key=lambda x: -x[1])[:20]:
    print("    + %-34s x%d  (=%r)" % (k, n, defaultSolution[k]))

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
