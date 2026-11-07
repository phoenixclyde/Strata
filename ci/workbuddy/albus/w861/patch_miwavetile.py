#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_patch_miwavetile.py -- 给 non-MI 路径补 MIWaveTile 族默认值。

`Solution.py:2219-2232` 里 MIWaveTileA/B 只在 `if state["EnableMatrixInstruction"]:` 内设置，
但 `KernelWriterAssembly` 无条件读 `kernel["MIWaveTileA"]`（1140/1275/1375 行等）。
gfx906 走 non-MI，于是 KeyError。

这是同一族的第 4 个（前三个：NumLdsBlk、NumTotalPackedLoadsA、MIWaveTileA 本身），
根因一致：2026 版 TensileLite 的 non-MI 代码路径缺乏测试覆盖。这里统一在分支前 setdefault，
不改变任何 MI 行为（MI 路径本来就会覆盖）。
"""
P = "/src/projects/hipblaslt/tensilelite/Tensile/SolutionStructs/Solution.py"
src = open(P, encoding="utf-8").read()
if "_W861_MIWAVETILE" in src:
    print("already patched")
    raise SystemExit(0)

anchor = '    if state["ProblemType"]["Tensor0"]==0:'
assert anchor in src, "anchor not found"
patch = (
    "    # _W861_MIWAVETILE: non-MI 路径不设 MIWaveTile*，但 KernelWriterAssembly 无条件读\n"
    '    state.setdefault("MIWaveTile", [1, 1])\n'
    '    state.setdefault("MIWaveTileA", 1)\n'
    '    state.setdefault("MIWaveTileB", 1)\n'
)
src = src.replace(anchor, patch + anchor, 1)
open(P, "w", encoding="utf-8").write(src)
print("patched")
