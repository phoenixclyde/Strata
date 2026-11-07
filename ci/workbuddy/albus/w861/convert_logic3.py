#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert3.py -- 旧 9 元素 LibraryLogic -> 新 loader 要的 12 元素，并展开锚点。

LibraryIO.parseLibraryLogicList 的位置约定（roc-libs 2026-10 版）：
  [0] MinimumRequiredVersion  [1] ScheduleName  [2] ArchitectureName  [3] DeviceNames
  [4] ProblemType             [5] Solutions     [6] IndexOrder        [7] ExactLogic
  [8] RangeLogic              [9] TileSelectionIndices  [10] PerfMetric
  [11] LibraryType(=distance) [12] DefaultSolution
旧 rocBLAS vega20 那份只有 [0..8]，缺 [9][10][11]。补：
  [9]=None（matching-table 文件里通常为空）, [10]=None, [11]=distance
distance 取 "Euclidean"（旧 Tensile matching table 的默认距离）。
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
print("top len after :", len(d), " [11] =", d[11])

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
