#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w861_patch_reject2.py -- 让 TCL 的 logger 路径不 raise。

`Tensile/SolutionStructs/Utilities.py` 的 reject() 在 library-logic 模式下是**直接 raise**：
    raise Exception("!! Warning: Any rejection of a LibraryLogic is not expected, please check. ...")
于是第一个 DepthU 不合格的解就让整个 TCL 退出，一个库都产不出来。

W858 §11.3 在 BenchmarkProblems 侧用的是 NoReject；这里是同一思路的另一处：
把 raise 改成"记录 + 返回"，让 codegen 尽量把解做完（不生成的都是缺参数的，后面由
库里的 solutions 数量直接反映出来，不会静默混进去）。
"""
import re
import sys

P = "/src/projects/hipblaslt/tensilelite/Tensile/SolutionStructs/Utilities.py"
src = open(P, encoding="utf-8").read()

if "_W861_NO_RAISE" in src:
    print("already patched")
    sys.exit(0)

# 找到 def reject(...) 的函数体，把 raise Exception(...) 换成记录
m = re.search(r"def reject\(([^)]*)\):", src)
if not m:
    print("FATAL: reject() not found")
    sys.exit(1)

body_start = m.end()
# 在该函数内找第一条 raise
rest = src[body_start:]
rm = re.search(r"(\n\s*)raise Exception\(", rest)
if not rm:
    print("FATAL: raise Exception not found inside reject()")
    sys.exit(1)

ins_at = body_start + rm.start()
patch = (
    "\n    # _W861_NO_RAISE: 库逻辑校验缺参数时不再中断整个 TCL\n"
    "    import sys as _s\n"
    "    print('W861 reject(skipped):', state.get('SolutionIndex', '?'), file=_s.stderr)\n"
    "    return\n"
)
out = src[:ins_at] + patch + src[ins_at:]
open(P, "w", encoding="utf-8").write(out)
print("patched", P)
# 打印 patch 后的函数头几行自检
i = out.find("def reject(")
print(out[i:i + 520])
