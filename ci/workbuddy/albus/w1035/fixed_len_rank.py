"""W1035 第 31 段：固定 2.5K 带的绝对值排序 → 撤回「R46 前移」建议，GEMM 仍是第一。

关键：斜率排序被截距污染；固定长度看绝对值才是对的。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035ab"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 固定 2.5K 带绝对值排序 → 撤回「R46 前移」】**：n=10、内容全新、tokens **2456–2538**、"
          "wall **3489 ms（CV 0.9%）**；各相位 CV 均 <=1.8%。**绝对值**："
          "gemm gate/up **754 ms（21.6%）** > down **455（13.0%）** > gdn **442（12.7%）** > "
          "qsa attn **348（10.0%）** > qsa proj 175（5.0%）> **dequant 169（4.8%）** > gdn out proj 166 > "
          "hc read(down+silu) 144 > gdn recurrence 144 > router 125 > hc read(up) 124 > host grouping 106；"
          "**top8 之和 2654 ms = 76%**。"
          "⇒ **2.5K 带第一是 gemm gate/up（21.6%），qsa attn 只有 10%**，与上一轮「按斜率排序 attn 第一」**相反**。"
          "**原因**：斜率的截距污染——gate/up 的固定项大，被 `b` 吃掉后斜率被低估；attn 固定项小、斜率接近真值。"
          "⇒ **上一轮那条「`R46` 应前移到 `R95` 之前」的建议撤回**；按固定长度绝对值，**GEMM 两相位合计 34.6% 仍是第一战场**，"
          "原队列顺序（`R95` 在 `R46` 前）是对的。"
          "**顺带一致性好**：`dequant 4.8%` 与 §0.1 记录的 `dequant 161 ms（5.0%）` 吻合，说明本测法与既有口径对齐。")

SEC = """
**31. 固定 2.5K 带看绝对值：GEMM 仍是第一，`qsa attn` 只有 10%——撤回上一条的队列建议。**
上一轮我用「跨 0.4–4K 的斜率」排序，得出 `qsa attn` 第一，并建议把 `R46` 前移。按新定的测法（**固定长度带**）重做：

n=10、内容全新、tokens **2456–2538**、wall **3489 ms（CV 0.9%）**，各相位 CV 都 ≤1.8%：

| 相位 | 均值 ms | 占 wall |
|---|---|---|
| **gemm gate/up** | **754** | **21.6%** |
| **gemm down** | **455** | **13.0%** |
| gdn | 442 | 12.7% |
| **qsa attn** | **348** | **10.0%** |
| qsa proj | 175 | 5.0% |
| **dequant** | **169** | **4.8%** |
| gdn out proj | 166 | 4.7% |
| hc read: down+silu | 144 | 4.1% |
| gdn recurrence | 144 | 4.1% |
| router+shared | 125 | 3.6% |
| hc read: up | 124 | 3.6% |
| host grouping | 106 | 3.0% |

（top8 之和 2654 ms = **76%**，其余零碎项占 24%。）

**两条修正**
1. **队列建议撤回**：按固定长度绝对值，**GEMM 两相位 34.6% 仍是第一战场**，`qsa attn` 只有 10%。
   ⇒ **原队列顺序（`R95` 在 `R46` 之前）是对的**，我上一轮"`R46` 应前移"作废。
2. **斜率排序本身不可用于排优先级**：`gate/up` 的固定项大，被截距 `b` 吃掉后**斜率被低估**（139 vs 真实 754/2500＝302 µs/tok），
   而 `attn` 固定项小、斜率接近真值 ⇒ 斜率比出来的是"谁的增长快"，不是"谁现在最贵"。
   **要排优先级必须看固定长度下的绝对值。**

**一致性检查（顺手做）**：`dequant` 在这里是 **169 ms / 4.8%**，与 §0.1 记录的「dequant 161 ms（5.0%）」吻合到 5% 内，
说明本测法与既有口径对齐，不是另起一套数。

**这条也解释了为什么前面几轮我反复改口**：我一直在「跨长度的斜率」和「定长的绝对值」之间来回切，
而这两者回答的是**不同问题**（增长 vs 现状）。**从这轮起：排优先级只看定长绝对值；斜率只用于外推。**
"""

PLAN_ADD = """
**补充 18（同日，定长绝对值排序）**：n=10、tokens 2456–2538、wall 3489 ms（CV 0.9%）⇒ **gemm gate/up 754（21.6%）> down 455（13.0%）> gdn 442（12.7%）> qsa attn 348（10.0%）**，dequant 169（4.8%）；top8=76%。⇒ **2.5K 第一战场仍是 GEMM（34.6%）**，**撤回「`R46` 前移」建议**，原队列顺序正确。**方法纪律**：斜率受截距污染（gate/up 斜率 139 vs 定长 302 µs/tok）⇒ **排优先级只看定长绝对值，斜率只用于外推**。一致性：dequant 4.8% ≈ §0.1 的 5.0%。
"""

MEMSEC = """
- 05:4x **定长排序 → 撤回 R46 前移**：n=10、tokens 2456–2538、wall 3489（CV 0.9%）⇒ gate/up **754（21.6%）** > down 455（13.0%）> gdn 442（12.7%）> qsa attn **348（10.0%）**，dequant 169（4.8%）。**GEMM 合计 34.6% 仍是第一战场**，原队列（R95 先于 R46）正确。**方法纪律：斜率受截距污染（gate/up 斜率 139 vs 定长 302）⇒ 排优先级看定长绝对值，斜率只作外推。**
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "固定 2.5K 带绝对值排序" in t:
        return "P418 已记定长排序"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加定长排序"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "31. 固定 2.5K 带看绝对值" in t:
        return "§31 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§31 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 18（同日，定长绝对值排序）" in t:
        return "方案补充 18 已存在"
    anchor = "**补充 17（同日，相位排序分区制）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 18 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "定长排序 → 撤回 R46 前移" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
