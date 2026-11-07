"""W1035 第 29 段：8 个长度点重算固定项 → 51%/49% 被 24%/21% 取代（P418 修正）。

同时记：launch 计数只在 STRATA_MMQ_DEBUG_J 开着时才有，多长度扫描默认拿不到 launches。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035z"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 8 点重算：固定项比先前报的小】**：同一容器内补 6 档（425/945/1626/2703/3956/5925 tok）"
          "连同已有 2 档（2054/4041），按 `T=a·n+b`：**wall = 1.24 ms/tok + 668 ms**（2K 处固定项占 **21%**，"
          "先前 3 点拟合报的 26% 偏高）；**gemm gate/up = 0.248 ms/tok + 167 ms**（占 **24%**，"
          "**先前报 51% 是错的**——那个 3 点拟合被偏高的 8K 点抬起了 b）；down 同量级。"
          "⇒ **固定项真实存在但比先前小一半**：2K 每 token 贵 1.57× 里面，约 **1/4 是固定项、3/4 是每 token 成本**。"
          "**另一个坑**：`pick_J` 只在 `STRATA_MMQ_DEBUG_J` 开着时才有，关掉后多长度扫描**拿不到 launches** ⇒ "
          "「用 launches 解释 wall」的实验必须**在该 env 开着的那一个窗口内把长度档一次打全**，不能分两次做。"
          "**数字纪律**：3 点拟合 + 一个离群点 = 会系统性高估截距；**长度档 >=6 个再报 b**。")

SEC = """
**29. 用 8 个长度点重算：固定项只有 21–24%，我先前报的 51% 是错的。**
先前那个「gate/up 固定项占 2K 的 51%」来自**三点拟合（2083/8244/16340）**，而 8K 点明显高于 2K–16K 直线
（我记录过"超预测 8%"，但没意识到它会**把截距抬高**）。现在在同一容器内补了 6 档，8 点一起拟合：

| 量 | 拟合 | 2K 处固定项占比 |
|---|---|---|
| wall | **1.24 ms/tok + 668 ms** | **21%** |
| gemm gate/up | **0.248 ms/tok + 167 ms** | **24%** |

**⇒ 先前报的 26% / 51% / 49% 全部作废，改用 21% / 24%**。固定项**真实存在但比先前小一半**：
2K 每 token 贵 1.57× 里，约 **1/4 来自固定项、3/4 来自每 token 成本**。
这一条直接改变了 `R95` 的优先级——**主战场回到每 token 成本（a=0.248 ms/tok 的 gate/up），不是固定项**。

**又踩一个坑（第四次同类）**：`pick_J` 行只在 `STRATA_MMQ_DEBUG_J` 开着时产生。我补的这 6 档是在该 env 关掉之后跑的，
所以**launches 全是 0**，`logfit` 把它们全过滤了——「用 launches vs tokens 争解释力」的实验**必须在一个窗口内把长度档打全**，
分两次做等于白做。已写进方案。

**数字纪律（新）**：**3 点拟合 + 一个离群点会系统性高估截距**；**报 `b` 之前长度档必须 >=6 个**。
这一条比先前"2×CV"更要紧——2×CV 管噪声，这条管**模型形状**。
"""

PLAN_ADD = """
**补充 16（同日，8 点重算）**：同容器补 6 档（425–5925 tok）+ 已有 2 档 ⇒ **wall = 1.24 ms/tok + 668 ms（2K 固定项 21%）**、**gate/up = 0.248 ms/tok + 167 ms（24%）** ⇒ **先前 26%/51%/49% 作废**；2K 的 1.57× 里约 **1/4 固定项、3/4 每 token**，主战场回到每 token 成本。**坑**：`pick_J` 只在 `STRATA_MMQ_DEBUG_J` 开着时有 ⇒ launches 对比必须**一个窗口内把长度档打全**。**数字纪律：长度档 >=6 才报 b；3 点 + 离群点会高估截距。**
"""

MEMSEC = """
- 05:2x **8 点重算，固定项缩水**：补 6 档（425–5925 tok）⇒ **wall=1.24 ms/tok+668 ms（2K 固定 21%）**、**gate/up=0.248 ms/tok+167 ms（24%）** ⇒ **先前 26%/51%/49% 作废**；2K 的 1.57× 里 **1/4 固定项、3/4 每 token**。**坑**：`pick_J` 仅在 `STRATA_MMQ_DEBUG_J` 开时有 ⇒ launches 对比必须一个窗口打全长度档。**数字纪律：长度档≥6 才报 b。**
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "8 点重算：固定项比先前报的小" in t:
        return "P418 已记 8 点重算"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加 8 点重算"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "29. 用 8 个长度点重算" in t:
        return "§29 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§29 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 16（同日，8 点重算）" in t:
        return "方案补充 16 已存在"
    anchor = "**补充 15（同日，三处更正 + ③ 重开）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 16 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "8 点重算，固定项缩水" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
