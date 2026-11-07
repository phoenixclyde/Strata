# -*- coding: utf-8 -*-
"""fix_lib2yaml.py -- 修上游 TensileLibLogicToYaml 的一个 bug。

上游 formForkParams 里：
    if skipMI != True and isMatrixInsEnabled:
        temp = form9BitMIInst(currentIndexSolution)
    else:
        temp = "None"          # ← 字符串
    forkData.append(formGroups(temp))   # ← formGroups 期望 dict，于是 .items() 崩

gfx906 非 MI（VALU）正好走 else 分支，所以这个工具对 vega20 完全不可用。
修法：只在有 MI 时才 append（非 MI 就一个组都不加）。
"""
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else (
    "/src/projects/hipblaslt/tensilelite/Tensile/TensileLibLogicToYaml.py"
)

OLD = '''    if skipMI != True and isMatrixInsEnabled:
        temp = form9BitMIInst(currentIndexSolution)
    else:
        temp = "None"

    forkData.append(formGroups(temp))'''

NEW = '''    if skipMI != True and isMatrixInsEnabled:
        forkData.append(formGroups(form9BitMIInst(currentIndexSolution)))
    # W860 fix: non-MI (gfx906 VALU) appends nothing; upstream passed the string "None"
    # into formGroups() which expects a dict -> AttributeError: 'str' has no attribute 'items'
'''

# 补丁 2：老格式（rocBLAS 4.6.0 时代的 LibraryLogic）没有 BiasDataTypeList 字段，
# 新工具直接下标取 -> KeyError。老 logic 的 _BH 里 B 是 beta 不是 bias，所以默认 [] 是对的。
OLD2 = '    biasTypeArgs = problemTypeStat["BiasDataTypeList"]'
NEW2 = '    biasTypeArgs = problemTypeStat.get("BiasDataTypeList", [])  # W860 fix: legacy logic has no such key'

OLD3 = '    gateTypeArgs = problemTypeStat.get("GateResidualDataTypeList", [])'
NEW3 = OLD3

s = io.open(P, encoding="utf-8").read()
changed = []
for tag, old, new in (
    ("non-MI-append", OLD, NEW),
    ("BiasDataTypeList", OLD2, NEW2),
):
    if new.split("\n")[0] in s and tag != "BiasDataTypeList":
        continue
    if old in s:
        s = s.replace(old, new, 1)
        changed.append(tag)
if changed:
    io.open(P, "w", encoding="utf-8").write(s)
    print("  patched:", ", ".join(changed), P)
else:
    print("  nothing to patch (already done?)")
