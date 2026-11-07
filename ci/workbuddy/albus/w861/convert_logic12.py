#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_convert12.py -- 在 11 的基础上做**类型归一化**（最后一道机械校验）。

TCL 的 TypeValidationErrors 说得非常具体：
  DirectToLds / PrefetchGlobalRead / PrefetchLocalRead / UseSgprForGRO / VectorStore
      -> found bool, expected int      (msgpack 里 bool 与 int 是两种 wire type，会 std::bad_cast)
  Use64bShadowLimit -> found int, expected bool
不硬编码这 6 个：直接问 `validParameters` 每个键声明的是什么类型，按声明转。
"""
import sys
import yaml

sys.path.insert(0, "/src/projects/hipblaslt/tensilelite")
from Tensile.Common.ValidParameters import validParameters  # noqa: E402

NEW = ("/src/projects/hipblaslt/library/src/amd_detail/rocblaslt/src/Tensile/"
       "Logic/asm_full/gfx950/gfx950/Equality/"
       "gfx950_Cijk_Ailk_Bjlk_HHS_BH_BiasSH_HAS_SAV_UserArgs.yaml")

KEEP_ASSERT = {
    "AssertAIGreaterThanEqual", "AssertAILessThanEqual",
    "AssertFree0ElementMultiple", "AssertFree1ElementMultiple",
    "AssertSummationElementMultiple",
}
GFX906 = {"EnableMatrixInstruction": False, "MatrixInstruction": [],
          "WavefrontSize": 64, "KernelLanguage": "Assembly", "NoReject": True}


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def want(keys):
    """validParameters 里这个键允许哪些 python 类型？
    注意：不是所有键的值都是"允许值列表"，有些直接是单个数（范围值），要跳过。"""
    if keys is None or not isinstance(keys, (list, tuple, set, frozenset)):
        return None
    if not keys:
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
    t = want(validParameters.get(k))
    if t is int and isinstance(v, bool):
        return int(v)
    if t is bool and isinstance(v, int) and not isinstance(v, bool):
        return bool(v)
    return v


def fix(s, stats):
    for k in list(s.keys()):
        nv = coerce(k, s[k])
        if nv is not s[k] and type(nv) is not type(s[k]):
            stats[k] = stats.get(k, 0) + 1
            s[k] = nv


src, dst = sys.argv[1], sys.argv[2]
tmpl = yaml.safe_load(open(NEW, encoding="utf-8"))
d = yaml.safe_load(open(src, encoding="utf-8"))

merged = dict(tmpl["DefaultSolution"])
merged.update(tmpl["Solutions"][0])
merged.update(GFX906)
merged.pop("ISA", None)
ds = dict(tmpl["DefaultSolution"])
ds.update(GFX906)
ds.pop("ISA", None)

for k, v in tmpl["ProblemType"].items():
    if k not in d[4]:
        d[4][k] = v

while len(d) < 13:
    d.append(None)
d[9] = None
d[10] = tmpl.get("PerfMetric")
d[11] = tmpl.get("LibraryType") or "Euclidean"
d[12] = ds

stats = {}
for s in d[5]:
    if not isinstance(s, dict):
        continue
    for k, v in merged.items():
        if k not in s or s[k] is None:
            s[k] = v
    s.update(GFX906)
    s.pop("ISA", None)
    for k in list(s.keys()):
        if k.startswith("Assert") and k not in KEEP_ASSERT:
            del s[k]
    fix(s, stats)
fix(d[12], stats)

print("类型修正:", stats)
print("Solution[0] 键数:", len(d[5][0]))

with open(dst, "w", encoding="utf-8") as fh:
    yaml.dump(d, fh, Dumper=NoAliasDumper, default_flow_style=False,
              sort_keys=False, allow_unicode=True, width=4096)
txt = open(dst, encoding="utf-8").read()
print("anchors left:", txt.count("&id") + txt.count("*id"), " bytes:", len(txt))
