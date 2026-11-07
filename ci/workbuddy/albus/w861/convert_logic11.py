#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert11.py -- 旧 9 元素 logic -> TCL 可消费（用 gfx950 的 Solution[0] + DefaultSolution 双模板）。

上一轮只用了 DefaultSolution，仍缺 ExpertSchedulingMode；gfx950 的 Solution[0] 有 161 键，
比 DefaultSolution 更接近"引擎真正会读到的字段集"。两个模板合并，缺谁补谁。

模板值里 gfx906 不相容的几项强制改写：
  EnableMatrixInstruction=False, MatrixInstruction=[], WavefrontSize=64,
  KernelLanguage=Assembly, ISA 删除（交给 gfxToIsa）
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

ds = dict(tmpl["DefaultSolution"])
s0 = dict(tmpl["Solutions"][0])
print("模板: DefaultSolution %d 键, Solution[0] %d 键, Sol0-DS 独有 %d"
      % (len(ds), len(s0), len(set(s0) - set(ds))))

# 合并模板（Solutions[0] 优先，因为它是"实际解"的完整字段集）
merged = dict(ds)
merged.update(s0)

# gfx906 强制项
GFX906 = {
    "EnableMatrixInstruction": False,
    "MatrixInstruction": [],
    "WavefrontSize": 64,
    "KernelLanguage": "Assembly",
    "NoReject": True,
}
merged.update(GFX906)
merged.pop("ISA", None)          # ISA 由 gfxToIsa(ArchitectureName) 决定
ds.update(GFX906)
ds.pop("ISA", None)

# ProblemType 补到 86 键
n_pt = 0
for k, v in tmpl["ProblemType"].items():
    if k not in d[4]:
        d[4][k] = v
        n_pt += 1

# 顶层 13 元素
while len(d) < 13:
    d.append(None)
d[9] = None
d[10] = tmpl.get("PerfMetric")
d[11] = tmpl.get("LibraryType") or "Euclidean"
d[12] = ds

# 每个解：合并模板补全 + 强制项 + 剔废弃 Assert
added = {}
for s in d[5]:
    if not isinstance(s, dict):
        continue
    for k, v in merged.items():
        if k not in s or s[k] is None:
            s[k] = v
            added[k] = added.get(k, 0) + 1
    s.update(GFX906)
    s.pop("ISA", None)
    for k in list(s.keys()):
        if k.startswith("Assert") and k not in KEEP_ASSERT:
            del s[k]

print("ProblemType +%d -> %d" % (n_pt, len(d[4])))
print("解补全字段 %d 种; 例: %s" % (len(added), sorted(added)[:10]))
print("Solution[0] 现有键数:", len(d[5][0]))

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
