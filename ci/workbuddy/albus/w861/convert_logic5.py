#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert5.py -- 旧 9 元素 logic -> 新 loader。

四件事：
1) 顶层补齐 12 元素（[9]=TileSelection, [10]=PerfMetric, [11]=distance）
2) 展开 YAML 锚点（AliasEvent 会让 CustomYamlLoader 状态机错位）
3) 每个 Solution 补 `EnableMatrixInstruction`
   —— 上游 Solution.py:846 有"缺失则推断"的分支，但推断完没写回 state，
      928 行 `state["EnableMatrixInstruction"]` 直接 KeyError。
      gfx906 无矩阵指令，值是确定的 False，不需要推断。
4) 顺带补 `UseDotInstruction`（928 行会根据上一项算，但有些分支先读）

其他缺失键交给引擎自己的 defaultSolution（LibraryIO.py:660-669 会补）。
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

FORCE = {
    "EnableMatrixInstruction": False,   # gfx906 无 MFMA/WMMA
}
added = {}
for s in d[5]:
    if not isinstance(s, dict):
        continue
    for k, v in FORCE.items():
        if k not in s:
            s[k] = v
            added[k] = added.get(k, 0) + 1

print("solutions:", len(d[5]), " 强制补:", added)

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
