# -*- coding: utf-8 -*-
"""patch_cfg.py -- 把 rocBLAS 4.6.0 时代反解出来的 config 调到 TensileLite 5.0.0 能接受。

为什么逐条改（都是实测撞出来的，不是猜）：
1. MinimumRequiredVersion 4.6.0 -> 5.0.0          否则 "not compatible with current Tensile version"
2. UseSgprForGRO [false] -> [0]                    否则 ConfigTypeError: expected int
3. VectorStore [true] -> [1]                       同上
4. 加 PrintSolutionRejectionReason: true           否则 reject 原因不可见
5. 加 WorkGroup [[64,4,1]]                         默认 [16,16,1] 会让 MIWaveGroup[0] = 16//64 = 0（除零）
6. ThreadTile [[2,2]] -> [[2,8]]                   MacroTile 128x8 时 totalVectorsB 算出负数
7. 加 GlobalReadVectorWidthA/B / VectorWidthA/B = 1 默认 -1 不在 [1,2,4,8,16,32] 里，静默置 validDepthU=False
8. 加 LocalReadVectorWidth = 1                     "LocalReadVectorWidth must equal VectorWidthA/B for MAC kernels"
"""
import io
import sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8").read()

s = s.replace("MinimumRequiredVersion: 4.6.0", "MinimumRequiredVersion: 5.0.0")
s = s.replace("- UseSgprForGRO: [false]", "- UseSgprForGRO: [0]")
s = s.replace("- VectorStore: [true]", "- VectorStore: [1]")

if "PrintSolutionRejectionReason" not in s:
    s = s.replace("GlobalParameters:\n", "GlobalParameters:\n  PrintSolutionRejectionReason: true\n", 1)

inject = (
    "    - WorkGroup: [[64, 4, 1]]\n"
    "    - ThreadTile: [[2, 8]]\n"
    "    - GlobalReadVectorWidthA: [1]\n"
    "    - GlobalReadVectorWidthB: [1]\n"
    "    - VectorWidthA: [2]\n"
    "    - VectorWidthB: [2]\n"
    "    - LocalReadVectorWidth: [2]\n"
)
old_tt = "    - ThreadTile: [[2, 2]]\n"
if old_tt in s:
    s = s.replace(old_tt, inject, 1)
elif "WorkGroup: [[64, 4, 1]]" not in s:
    # 兜底：插在 DepthU 之前
    s = s.replace("    - DepthU:", inject + "    - DepthU:", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("  patched", P)
