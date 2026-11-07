"""W1035 第 30 段：每 token 成本的相位排序是「分区制」的；2K 带第一名是 qsa attn 不是 GEMM。

含一处自相矛盾的暴露：8 点干净集给 gate/up 248 µs/tok，分桶给 139 —— 两个方法不一致，必须写清楚为什么。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035aa"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 每 token 成本排序（分长度桶）】**：318 个干净点（当前容器）按桶拟合："
          "**0.4–4K（n=598 条含重复）**：wall 867 µs/tok，**qsa attn 192 > gdn 155 > gemm gate/up 139 > down 122**；"
          "**4–16K（n=199）**：qsa attn 216 > gate/up 200 > gdn 161 > down 140；"
          "**16–64K（n=67）**：qsa attn **423**（随长度超线性）> gate/up 318 > hc read 236。"
          "⇒ **在 <=4K 带，每 token 成本第一名是 qsa attn，不是 GEMM**（与 `P104` 的 M/L 分档口径一致，但比它更细）。"
          "**队列含义**：`R46`（prompt attn 效率）在 §0.1 里排第 6，按本表应提到 `R95` 之前——这条只作建议，不改队列。"
          "**自相矛盾必须写出来**：8 点干净集给 gate/up **248 µs/tok**，分桶给 **139**；两者差 78%，"
          "原因是**斜率随区间变**（8 点跨 425–5925 tok，桶内只看 0.4–4K），**说明 `T=a·n+b` 只在窄带内成立**。"
          "⇒ **正确测法**：**固定长度带（1.8–2.2K）、n>=8、只改内容**，再做相位对比；跨长度比斜率会把排序带偏。"
          "**另一处异常**：0.4–4K 桶截距 **1929 ms** 偏大，说明该桶混进了大量短提示（~400 tok），"
          "低端非线性和截距互相污染 ⇒ **桶内也要砍掉 <1K 的点**。")

SEC = """
**30. 每 token 成本的排序是分区制的：2K 带第一名是 `qsa attn`，不是 GEMM。**
`R95` 主战场切到每 token 成本后，第一个要回答的是「哪一项在吃」。用同一容器的干净日志按长度分桶：

| 桶 | n | wall | 第一名 | 第二名 | 第三名 |
|---|---|---|---|---|---|
| **0.4–4K** | 598 | 867 µs/tok | **qsa attn 192** | gdn 155 | gate/up 139 |
| 4–16K | 199 | 1077 µs/tok | **qsa attn 216** | gate/up 200 | gdn 161 |
| 16–64K | 67 | 1837 µs/tok | **qsa attn 423** | gate/up 318 | hc read 236 |

（µs/token；64K+ 桶 n=11、截距 89 s，明显不可用，直接弃。）

**三条结论**
1. **`qsa attn` 在 <=16K 全部区间都是第一名**，且随长度超线性（192 → 216 → 423）。这就是"长上下文变慢"的主要来源。
2. **队列含义**：`R46`（prompt attn 效率）在 §0.1 里排第 6，按本表**应提到 `R95` 之前**。我只写建议，**不自行改队列**。
3. **8 点与分桶互相矛盾，必须摊开说**：干净 8 点集给 gate/up **248 µs/tok**，0.4–4K 桶给 **139**，差 78%。
   原因不是谁算错了，而是**斜率随区间变**——8 点跨 425–5925 tok，`T=a·n+b` 在这么宽的带里已经不成立。
   ⇒ **`T=a·n+b` 只在窄带内可信**；要排相位优先级，**必须固定长度带（1.8–2.2K）、n≥8、只改内容**。

**另一处异常（同源）**：0.4–4K 桶截距 **1929 ms** 偏大，因为桶里混进了 ~400 tok 的短提示，
低端非线性把截距抬了起来 ⇒ **桶内还得再砍掉 <1K**。

**所以下一手不是再拟合，而是把测量方式定死**：固定 2K 带、n≥8、同内容不同 seed、逐相位。
这条做完，才能说"2K 该先优化谁"。**在此之前，本表只能当"排序指示"，不能当"量值"。**
"""

PLAN_ADD = """
**补充 17（同日，相位排序分区制）**：按桶拟合（当前容器干净日志）——**0.4–4K**：qsa attn 192 > gdn 155 > gate/up 139 > down 122（µs/tok）；**4–16K**：attn 216 > gate/up 200；**16–64K**：attn 423。⇒ **<=16K 每 token 第一名是 qsa attn**，**建议把 `R46` 提到 `R95` 之前**（仅建议，不改 §0.1 队列）。**自相矛盾已记录**：8 点集 gate/up 248 vs 桶内 139（差 78%）⇒ **`T=a·n+b` 只在窄带成立**；正确测法=固定 1.8–2.2K、n≥8、只改内容；桶内还要砍 <1K（截距 1929 ms 被短提示抬高）。
"""

MEMSEC = """
- 05:3x **相位排序分区制**：0.4–4K qsa attn **192** > gdn 155 > gate/up 139 > down 122（µs/tok）；4–16K attn 216；16–64K attn 423 ⇒ **<=16K 第一名是 qsa attn**，建议 `R46` 提前（仅建议）。**矛盾记录**：8 点集 gate/up 248 vs 桶内 139（差 78%）⇒ **T=a·n+b 只在窄带成立**；正确测法=固定 1.8–2.2K、n≥8、只改内容、砍 <1K。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "每 token 成本排序（分长度桶）" in t:
        return "P418 已记排序"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加相位排序"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "30. 每 token 成本的排序是分区制的" in t:
        return "§30 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§30 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 17（同日，相位排序分区制）" in t:
        return "方案补充 17 已存在"
    anchor = "**补充 16（同日，8 点重算）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 17 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "相位排序分区制" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
