#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert9.py -- 用「别的架构」（gfx950）的新格式 logic 当模板，而不是拿旧文件打补丁。

依据 gfx950 那份新格式（dict，14 键）：
    MinimumRequiredVersion / ScheduleName / ArchitectureName / CUCount / DeviceNames
    ProblemType(86 键) / **DefaultSolution(165 键)** / Solutions(49 个，各 161 键)
    IndexOrder / ExactLogic / RangeLogic / TileSelectionIndices / PerfMetric / LibraryType

关键在 DefaultSolution：`LibraryIO.py:660-666` 的 solutionStateToSolution() 会先拿它补缺失键
（`for key, val in libDefaults.items(): if key not in solutionState: ...`）。
旧 rocBLAS logic 是 9 元素 list，`parseLibraryLogicList` 把 data[12] 读成 DefaultSolution
—— 于是把 gfx950 的 165 键默认解（MI 相关改成 gfx906 的值）放进 [12]，
128 个旧解缺的所有新字段，引擎自己会填，不用逐个猜。

同时：
  ProblemType 37 -> gfx950 的 86 键（缺的照抄）
  顶层补到 13 元素（[9] TileSelection / [10] PerfMetric / [11] LibraryType / [12] DefaultSolution）
  展开 YAML 锚点、Solution 补 EnableMatrixInstruction=False + NoReject=True、剔除废弃 Assert*
"""
import sys
import yaml

NEW = ("/src/projects/hipblaslt/library/src/amd_detail/rocblaslt/src/Tensile/"
       "Logic/asm_full/gfx950/gfx950/Equality/"
       "gfx950_Cijk_Ailk_Bjlk_HHS_BH_BiasSH_HAS_SAV_UserArgs.yaml")

KEEP_ASSERT = {
    "AssertAIGreaterThanEqual", "AssertAILessThanEqual",
    "AssertFree0ElementMultiple", "AssertFree1ElementMultiple",
    "AssertSummationElementMultiple",
}


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


src, dst = sys.argv[1], sys.argv[2]

tmpl = yaml.safe_load(open(NEW, encoding="utf-8"))
d = yaml.safe_load(open(src, encoding="utf-8"))
print("旧顶层 %d 元素；模板 DefaultSolution %d 键 / ProblemType %d 键 / Solution[0] %d 键"
      % (len(d), len(tmpl["DefaultSolution"]), len(tmpl["ProblemType"]), len(tmpl["Solutions"][0])))

# --- ProblemType 补到 86 键 ---
n_pt = 0
for k, v in tmpl["ProblemType"].items():
    if k not in d[4]:
        d[4][k] = v
        n_pt += 1

# --- DefaultSolution：gfx950 的 165 键，但 MI 相关改成 gfx906 的值 ---
ds = dict(tmpl["DefaultSolution"])
ds["EnableMatrixInstruction"] = False
ds["MatrixInstruction"] = []
ds["NoReject"] = True
ds.pop("ISA", None)          # ISA 交给 gfxToIsa(ArchitectureName)，给 int 会 TypeError
ds["WorkGroup"] = [64, 4, 1]

# --- 顶层补到 13 元素 ---
while len(d) < 13:
    d.append(None)
d[9] = None                                   # TileSelectionIndices
d[10] = tmpl.get("PerfMetric")                # PerfMetric
d[11] = tmpl.get("LibraryType") or "Euclidean"  # LibraryType(=distance)
d[12] = ds                                    # DefaultSolution

# --- Solution 侧 ---
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

print("ProblemType +%d -> %d 键" % (n_pt, len(d[4])))
print("DefaultSolution 放入 [12]，%d 键" % len(ds))
print("剔除废弃 Assert:", dropped)

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
