"""W1035 第 36 段：算错 48 层 → 效率其实是 33–40%，「0.8% 神秘缺口」不存在，P297 不冲突。

这是本轮最重要的自我更正：前两轮关于「核效率」的结论全部撤回。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035ag"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 重大更正：漏乘 48 层 ⇒ 效率 33–40%，「0.8% 缺口」不存在】**：前两轮我把 gate/up 的 FLOPs 算成 "
          "164 GFLOP，**忘了乘 `block_count = 48`**。正确算式：2500 token × 10 专家 × 1280×2560 × 2 FLOP "
          "**× 48 层** = **7864 GFLOP（7.86 TFLOP）** ⇒ 下限 **296.8 ms**，实测 754 ms ⇒ **效率 39.4%**。"
          "注意力同法：2500 × 2048(稀疏 keys) × 128 × 2 × 24 头 × 2 × 48 层 = **3020 GFLOP** ⇒ 下限 114 ms，"
          "实测 348 ms ⇒ **效率 32.7%**。"
          "⇒ **两个主相位都在峰值的 33–40%，是完全正常的水平**；**不存在 0.8%/1.6% 的神秘缺口**，"
          "**`P297`（残余不在 MMQ 核内）不冲突、无需重审**，我上一轮登记的冲突**撤回**。"
          "**对 `R95` 的含义**：2K 的 1.57× 里 3/4 是每 token 成本，而每 token 成本已在 33–40% 峰值 ⇒ "
          "**没有明显可回收的浪费**；除非改算法（top-10 是模型属性，不能动）。⇒ **`R95` 建议结案为「无可优化空间」**。")

SEC = """
**36. 更正：我漏乘了 48 层——效率其实是 33–40%，"神秘缺口"不存在，`P297` 也不冲突。**
这是本轮最要紧的一条，因为它**推翻我前两轮的核心结论**。

**错在哪**：我把 2.5K 的 gate/up 算成 164 GFLOP，**忘了乘 `block_count = 48`**（每层都有一份 gate/up）。
正确算式：

| 相位 | FLOPs（含 48 层） | 下限 @26.5 TFLOPS | 实测 | 效率 |
|---|---|---|---|---|
| gemm gate/up | 2500×10×1280×2560×2×**48** = **7864 GFLOP** | 296.8 ms | 754 ms | **39.4%** |
| qsa attn | 2500×2048×128×2×24×2×**48** = **3020 GFLOP** | 114.0 ms | 348 ms | **32.7%** |

⇒ **两个主相位都在峰值的 33–40%**——对 gfx906 上的量化 GEMM 与稀疏注意力，这是**正常水平**，
与先前"满频 1725 MHz、200 W、GPU 99%"的观测**完全自洽**（本来就没有异常）。

**三处撤回**
1. ~~「MoE GEMM 只有峰值 0.8%」~~ → **39.4%，正常**；
2. ~~「缺口形状是核效率，指向 Q4_K 反量化 + tile 组织」~~ → **无缺口，不必攻**；
3. ~~「`P297`（残余不在 MMQ 核内）与之冲突，需重审」~~ → **不冲突，撤回该登记**。

**对 `R95` 的判决变了**：2K 的 1.57× 每 token 成本里，**3/4 是每 token 项**（`a`=0.248 ms/tok），
而这一项已在**峰值的 39%**，没有明显浪费；固定项占 21%，也只对应 ~150 ms 的一次性开销。
⇒ **`R95` 应结案为「无可优化空间（除改算法外）」**：top-10 是模型属性、48 层是模型属性、Q4_K 是既定档位。

**这一轮的元教训（比结论更贵）**：我连续两轮用同一个漏项的数字去推"异常"，还在其上登记了与既有结论的冲突。
**规则：报"效率/峰值占比"之前，必须先写出量纲与逐项因子的完整算式，并做一次量级自检**——
7.86 TFLOP 在 13–26 TFLOPS 的卡上"应该是几百毫秒"，而 164 GFLOP 只有 6 ms，
**两者差 48 倍，正好是我漏的层数；量级自检本来一秒就能抓出来**。
"""

PLAN_ADD = """
**补充 23（同日，重大更正：漏乘 48 层）**：gate/up 正确 FLOPs = 2500×10×1280×2560×2×**48** = **7864 GFLOP** ⇒ 下限 296.8 ms，实测 754 ms ⇒ **39.4%**；注意力 3020 GFLOP ⇒ 下限 114 ms，实测 348 ⇒ **32.7%**。⇒ **两主相位 33–40% 属正常**，**「0.8% 缺口」「核效率是问题」「与 `P297` 冲突」全部撤回**。**`R95` 建议结案为「无可优化空间」**（top-10/48 层/Q4_K 都是既定）。**纪律：报峰值占比前必须写全量纲与因子并做量级自检**（164 GFLOP 对 7864 GFLOP 差 48×，一秒可发现）。
"""

MEMSEC = """
- 06:4x **重大更正：漏乘 48 层**。gate/up 正确 7864 GFLOP（下限 296.8 ms，实测 754 ⇒ **39.4%**）；attn 3020 GFLOP（114 ms，实测 348 ⇒ **32.7%**）⇒ **两相位 33–40% 正常**，「0.8% 缺口」「核效率是问题」「与 P297 冲突」**全撤**。**R95 建议结案「无可优化空间」**（top-10/48 层/Q4_K 既定）。**纪律：报峰值占比前写全量纲与因子并做量级自检。**
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "漏乘 48 层" in t:
        return "P418 已记 48 层更正"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加 48 层更正"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "36. 更正：我漏乘了 48 层" in t:
        return "§36 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§36 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 23（同日，重大更正：漏乘 48 层）" in t:
        return "方案补充 23 已存在"
    anchor = "**补充 22（同日，排除降频）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 23 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "漏乘 48 层" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
