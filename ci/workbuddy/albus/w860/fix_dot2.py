# -*- coding: utf-8 -*-
"""fix_dot2.py -- 让 gfx906 走 v_dot2_f32_f16（DOT2 MAC 组件），绕开已废弃的 mad_mix 路径。

为什么：`MAC_F16_HPA.FMA_F16_HPA_MAD_MIX` 依赖 rocisa 的 `Module.addInst(...)` 老 API 与
`v_mad_mix_f32` 指令类，而当前 rocisa **两者都没有**（`grep MadMix|FmaMix rocisa/instruction.py` = 0）——
即上游把 gfx906 的 f16 HPA MAC 路径整个删了。

但 Vega20 **有** `v_dot2_f32_f16`（dot2 是 gfx906 引入的），而 `FMA_F16_HPA_DOT2` 组件是**新 API**
（`__call__(writer, tPA, tPB, m, innerUnroll)`，用 rocisa 的 `VDot2F32F16/VDot2CF32F16` 类）。
Tensile 只是把 UseDotInstruction 的 ISA 白名单卡在 gfx942/gfx950（Solution.py:928）。
把这一个条件放宽到 9.0.6 即可，不需要新写任何指令类。
"""
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else (
    "/src/projects/hipblaslt/tensilelite/Tensile/SolutionStructs/Solution.py"
)

s = io.open(P, encoding="utf-8").read()

if "ISA 9,0,6" in s and "isHalf()" in s and "W860" in s:
    print("  already patched")
    sys.exit(0)

# 目标片段（保持原缩进）
NEEDLE = '''    state["UseDotInstruction"] = (not state["EnableMatrixInstruction"]) \\
      and state["ProblemType"]["HighPrecisionAccumulate"] \\
      and ((state["ISA"] == IsaVersion(9,4,2) and state["ProblemType"]["DataType"].isHalf()) \\
      or (state["ISA"] == IsaVersion(9,5,0) and (state["ProblemType"]["DataType"].isBFloat16() or state["ProblemType"]["DataType"].isHalf())))'''

if NEEDLE not in s:
    print("  !! needle not found; dumping the region for inspection")
    i = s.find('state["UseDotInstruction"] =')
    print(s[i:i + 520] if i >= 0 else "(UseDotInstruction assignment not found)")
    sys.exit(1)

REPL = '''    state["UseDotInstruction"] = (not state["EnableMatrixInstruction"]) \\
      and state["ProblemType"]["HighPrecisionAccumulate"] \\
      and ((state["ISA"] == IsaVersion(9,4,2) and state["ProblemType"]["DataType"].isHalf()) \\
      or (state["ISA"] == IsaVersion(9,5,0) and (state["ProblemType"]["DataType"].isBFloat16() or state["ProblemType"]["DataType"].isHalf())) \\
      or (state["ISA"] == IsaVersion(9,0,6) and state["ProblemType"]["DataType"].isHalf()))  # W860: gfx906 has v_dot2_f32_f16'''

s = s.replace(NEEDLE, REPL, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("  UseDotInstruction extended to ISA 9,0,6")
