"""W1035 第 22 段：R51 分支结案 + R95 固定项分离（P418）。

一次落盘、单次执行。
"""
import io
import os
import re
import shutil
import subprocess
import sys

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035r"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


R51_NOTE = ("  **【W1035 结】10-19 栈分支 DONE_NEG**：前置 `P392` 已由 **`P407`** 静态结——`#29953` 只改缓冲区大小、"
            "tile 选择逐行等价，且我们 MoE 预填的 `q8_bytes()` 自带 128 块余量 ⇒ 该补丁**收益 0**；"
            "`P390` 另证 10-19 栈不掉速（534.83/716.72 vs 532.76/714.89）但同样无正收益。"
            "⇒ 不为它付停机，队列前移至 **R95**。")

ROW = ("B6判定探针\tP418\t小批 GEMM 的 1.23× 是「每次调用的固定项」，不是每 token 的核内成本"
       "\tW1035\tcount\t1\t1\tDONE\t"
       "**W1035 立（R95 下一手，零停机，用现成相位表）**：把 `PREFILL_PHASES.tsv` 的新 campaign 三档"
       "（2083 / 8244 / 16340 tok，每档 n=3）按 `T = a·n + b` 最小二乘分解——"
       "**gate/up：a=226.7 μs/token、b=415.6 ms**（固定项占 2K 实测 818 ms 的 **51%**）；"
       "**down：a=147.5、b=249.1 ms**（占 513 ms 的 **49%**）；**墙钟：a=1210.6、b=842.3 ms**（占 3210 ms 的 **26%**）。"
       "⇒ 「2K 每 token 贵 1.57×」**不是小批时核内每 token 变贵**，而是**每次 prefill 有一笔与长度无关的固定开销**，"
       "在 2K 这种小请求上摊不开。**各相位固定项之和 ≈ 807 ms**（gate/up 416 + down 249 + host grouping 80 + "
       "router 37 + wait copy 17 + combine 8）与墙钟 b=842 ms 只差 4% ⇒ **固定项主要住在两个 GEMM 相位里（82%）**，"
       "不在 host grouping / wait copy。**边界（不夸大）**：三点拟合在 8K 处对 2K-16K 直线**超预测 8%**，"
       "说明不是严格仿射（8K 略超线性）；`dequant` 的拟合误差 **49%**，其 b 不可用；`qsa attn` 得负 b，无物理意义。"
       "**下一手**：在固定项里分离「权重搬运」与「调度/建表」——需一次停机窗口（同 2K 形状，冷/热 expert-cache 对照）。"
       "\t\tKW:固定项|1.57|gate/up|416")


SEC = """
**22. 队列推进：`R51` 分支结案（DONE_NEG），`R95` 的「1.57×」被拆成固定项——结论改写了它的方向。**
按 §0.1 队列，第 1 序 `R51` 的前置就是 `P392`，而 `P407` 已把它静态结掉（补丁只改缓冲区大小、tile 选择逐行等价、
自家 `q8_bytes()` 自带 128 块余量 ⇒ 收益 0），`P390` 另证 10-19 栈不掉速但也没有正收益。
⇒ **10-19 分支 `DONE_NEG`，不为它付停机**，队列前移到 `R95`。

`R95` 的下一手是「量 host/launch」。这次零停机，直接用现成相位表做分解（`albus/w1035/r95_fit.py`，可复现）：

| 相位 | 每 token（μs） | 固定项 b（ms） | 2K 实测 | 固定项占比 |
|---|---|---|---|---|
| **gemm gate/up** | 226.7 | **415.6** | 818 ms | **51%** |
| **gemm down** | 147.5 | **249.1** | 513 ms | **49%** |
| 墙钟 | 1210.6 | **842.3** | 3210 ms | 26% |
| host grouping | −1.5 | 79.6 | 92 ms | —（**不随长度变**） |
| wait copy | 7.7 | 16.9 | 36 ms | — |
| router+shared | 34.9 | 37.5 | 109 ms | — |

**三条能落地的读数**
1. **`R95` 的 1.57× 不是"核内每 token 变贵"**，而是「每次 prefill 有一笔与长度无关的固定开销」，2K 摊不开。
   这与 `P297`（残余不在 MMQ 核内、`WIDTH_SWEEP` 每行成本平坦）**独立互证**。
2. **固定项主要住在两个 GEMM 相位里**：各相位固定项之和 ≈ **807 ms**（416+249+80+37+17+8），与墙钟 `b=842 ms` 只差 **4%**；
   其中 gate/up + down = 665 ms，占 **82%**。⇒ 下一步不该继续找"更快的小批 GEMM kernel"，
   该问"每次 prefill 在 GEMM 里固定花的那 665 ms 是什么"。
3. **`host grouping` 的 a=−1.5 μs/token**（≈0），即它**完全不随长度变**，是纯固定项 80 ms——
   这修正了它过去被当成"每层 sync"的读法（`P333` 已否过三个模型）。

**边界（不夸大，也不藏）**
- 三点拟合在 **8K 处对 2K-16K 直线超预测 8%** ⇒ 不是严格仿射，8K 略超线性；`b` 的量级可信、精确值不可信。
- `dequant` 的拟合误差 **49%**（2K 预测 239 vs 实测 160）⇒ 它的 `b` 不可用，别引用。
- `qsa attn` 拟合出**负 b**，无物理意义 ⇒ 该相位不能用 `T=a·n+b` 描述。

**下一手（要窗口）**：在同 2K 形状下做「冷 / 热 expert-cache」对照，把 665 ms 拆成「权重搬运」与「调度/建表」。
按项目铁律，这一步需要停机，我会先单独报窗口再动。
"""

PLAN_ADD = """
**补充 9（同日，队列推进）**：`R51` 的 10-19 分支 **DONE_NEG**（前置 `P392` 已由 `P407` 静态结，收益 0；`P390` 证明不掉速但无正收益）⇒ 队列前移 `R95`。`R95` 下一手（零停机，`albus/w1035/r95_fit.py`）：新 campaign 三档按 `T=a·n+b` 分解 ⇒ **gate/up 固定项 415.6 ms（占 2K 818 ms 的 51%）**、**down 249.1 ms（占 49%）**、墙钟 **842.3 ms（占 26%）**；各相位固定项之和 ≈ 807 ms 与墙钟 b 差 4%，其中 GEMM 两相位占 82% ⇒ **1.57× 是每次调用的固定开销，不是核内每 token 变贵**（与 `P297` 互证）。边界：8K 超预测 8%（非严格仿射）、`dequant` 拟合误差 49%、`qsa attn` 负 b 不可用。下一手需停机窗口拆「权重搬运 vs 调度/建表」。
"""

MEMSEC = """
- 04:3x **队列推进**：`R51` 10-19 分支 **DONE_NEG**（`P407` 静态结：补丁只改缓冲区、tile 等价、自带 128 块余量 ⇒ 收益 0）⇒ 前移 `R95`。**`P418`**：新 campaign 三档拟合 `T=a·n+b` ⇒ gate/up **b=415.6 ms（占 2K 51%）**、down **249.1（49%）**、墙钟 **842.3（26%）**；各相位固定项和 ≈807 ms 与墙钟差 4%，GEMM 两相位占 82% ⇒ **1.57× 是每次调用的固定开销，不是核内每 token 变贵**（与 `P297` 互证）。边界：8K 超预测 8%、`dequant` 误差 49%、`qsa attn` 负 b 不可用。下一手要窗口拆「权重搬运 vs 调度」。
"""


def add_r51():
    t = io.open(PROG, encoding="utf-8").read()
    if "10-19 栈分支 DONE_NEG" in t:
        return "R51 已记"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["R51"]:
            f[9] = (f[9].rstrip() + R51_NOTE).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "R51 已追加结案"
    return "R51 未找到"


def add_row():
    t = io.open(PROG, encoding="utf-8").read()
    if "\tP418\t" in t:
        return "P418 已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    idx = None
    for i, l in enumerate(lines):
        if l.split("\t")[1:2] == ["P417"]:
            idx = i
    if idx is None:
        return "P417 未找到"
    lines.insert(idx + 1, ROW)
    io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return "P418 已插到 P417 之后"


def fix_queue_and_denominator():
    r = subprocess.run([sys.executable, "tools/progress.py"], capture_output=True, text=True)
    m = re.search(r"条 (\d+) ／ 已结 (\d+)（([\d.]+)%）", r.stdout.splitlines()[0])
    if not m:
        return "progress 解析失败"
    n, d, pct = m.groups()
    t = io.open(PLAN, encoding="utf-8").read()
    outs = []
    # 分母
    cur = re.search(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1035 校正；", t)
    if cur and cur.group(0) != "**%s 条 / 已结 %s / %s%%**（W1035 校正；" % (n, d, pct):
        t = t.replace(cur.group(0), "**%s 条 / 已结 %s / %s%%**（W1035 校正；" % (n, d, pct), 1)
        outs.append("分母 %s/%s" % (n, d))
    # 队列：R51 -> DONE_NEG，R95 进行中
    old = ("**R51**（W1031 重开：先补 `P392` 的 prefill-only 数值门，再在 10-19 栈上限内做单点 A/B；"
           "账本 `R51` 仍记 W904 原题的 DONE_NEG，重开证据 `P390`/`P391`/`P392`）→ **R95**")
    new = ("~~**R51**（W1031 重开）~~ **W1035 结：10-19 分支 DONE_NEG**（前置 `P392` 已由 `P407` 静态结，收益 0）→ "
           "**R95**（进行中：`P418` 已把 1.57× 拆成「每次调用的固定项」gate/up 416 ms / down 249 ms；"
           "下一手需窗口拆「权重搬运 vs 调度/建表」）")
    if old in t:
        t = t.replace(old, new, 1)
        outs.append("队列 R51→DONE_NEG / R95 进行中")
    elif "R95**（进行中" in t:
        outs.append("队列已是新形态")
    else:
        outs.append("⚠ 队列原文未匹配")
    if outs:
        backup(PLAN)
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t)
    return "; ".join(outs)


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "22. 队列推进" in t:
        return "§22 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§22 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 9（同日，队列推进）" in t:
        return "方案补充 9 已存在"
    anchor = "**这道门正是为「按词搜不到」而建，它自己按词搜不到**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n", i)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + t[j:])
    return "方案补充 9 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "`P418`" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (add_r51, add_row, fix_queue_and_denominator, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
