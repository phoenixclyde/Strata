# -*- coding: utf-8 -*-
"""mk_ss_logic.py -- 从上游 gfx1100 的 SB.yaml 派生一份**朴素 SS（f32，无 Bias/无 SAV/无 Activation）**
的 gfx906 LibraryLogic，用于让 hipBLASLt 的 heuristic 能匹配最简单的 f32 GEMM 查询。

为什么不用 SB.yaml 原样：它是 `SS_HSS_BH_Bias_S_HA_S_SAV_UserArgs` —— 带 bias、带 ScaleAlphaVec、
带 activation，hipBLASLt 的 heuristic 按 problem type 严格匹配，探针查朴素 GEMM 必然 algos=0。

用法：python3 mk_ss_logic.py <src SB.yaml> <out yaml>
"""
import io
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
src = io.open(SRC, encoding="utf-8").read().split("\n")

# 精确到行首两空格的键，避免误伤解（Solutions）里的同名字段
REPL = {
    "- navi31": "- vega20",
    "- gfx1100": "- gfx906",
    "  Activation: true": "  Activation: false",
    "  UseBias: 1": "  UseBias: 0",
    "  UseScaleAlphaVec: 1": "  UseScaleAlphaVec: 0",
    "  BiasDataTypeList: [0]": "  BiasDataTypeList: []",
    "  StridedBatched: true": "  StridedBatched: false",
}

# 只改前 100 行（ProblemType 段），Solutions 段原样保留
out, hits = [], {k: 0 for k in REPL}
for i, ln in enumerate(src):
    if i < 100 and ln in REPL:
        out.append(REPL[ln])
        hits[ln] += 1
    else:
        out.append(ln)

io.open(OUT, "w", encoding="utf-8").write("\n".join(out))
print("wrote", OUT, "lines", len(out))
for k, v in hits.items():
    print("  %-28s -> %-24s x%d" % (k, REPL[k], v))
missing = [k for k, v in hits.items() if v == 0]
if missing:
    print("  !! 未命中:", missing)
