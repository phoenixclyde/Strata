# -*- coding: utf-8 -*-
"""fix_mac.py -- 把 MAC_F16_HPA.py 里的 FMA_F16_HPA_MAD_MIX 对齐到新 Component API。

实测：gfx906 的 f16（HPA）非 MI 路径唯一可用的 MAC 组件就是它（asmCaps: v_mad_mix_f32 / v_fma_mix_f32，
`v_mad_mix_f32` 正是 Vega20 的指令）。但同文件里 DOT2 已经是新签名 5 参，它还是老 3 参：
    调用方传 (writer, tPA, tPB, m, innerUnroll)  -> 报 "takes 4 positional arguments but 6 were given"
上一轮加 `*a, **kw` 后变成 "'dict' object cannot be interpreted as an integer"，因为 tPA/tPB 被吞进
`*a`，第 3 个位置参数 m 收到的是 tPB（dict）。

正确改法：签名照抄 DOT2，并把函数体里 4 处 writer.tPA / writer.tPB 换成参数。
"""
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else (
    "/src/projects/hipblaslt/tensilelite/Tensile/Components/MAC_F16_HPA.py"
)

OLD_SIG = "    def __call__(self, writer, m, innerUnroll):"
NEW_SIG = "    def __call__(self, writer, tPA, tPB, m, innerUnroll):  # W860: align with DOT2's new API"

lines = io.open(P, encoding="utf-8").read().split("\n")

# 只改 MAD_MIX 那个类（从 "class FMA_F16_HPA_MAD_MIX" 到文件末尾或下一个 class）
start = None
for i, ln in enumerate(lines):
    if ln.startswith("class FMA_F16_HPA_MAD_MIX"):
        start = i
        break
if start is None:
    print("  !! class FMA_F16_HPA_MAD_MIX not found")
    sys.exit(1)

changed = 0
for i in range(start, len(lines)):
    if i > start and lines[i].startswith("class "):
        break
    if lines[i] == OLD_SIG:
        lines[i] = NEW_SIG
        changed += 1
    lines[i] = lines[i].replace("writer.tPA", "tPA").replace("writer.tPB", "tPB")

io.open(P, "w", encoding="utf-8").write("\n".join(lines))
print("  MAC_F16_HPA patched: sig x%d, refs rewritten" % changed)
