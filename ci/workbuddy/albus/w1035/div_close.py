"""W1035 第 26 段：④ 的操作化被否；Zipf 对照把 +14.6% 定位到「重复」而非「路由集中」。

含一处样本剔除（hi#0 命中 prompt cache，0.38 s），以及一次自己写的 bug（词表 19 给 18 个权重）。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035w"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 候选④ 的操作化被否 + 新候选⑤】**：按 n=5、交错、长度差 <=3% 重做——"
          "`hi`（随机词序）**1548 ms/ktok**（CV 1.0%）vs `lo`（同一 18 词短语重复 108 次）**1774 ms/ktok**（CV 0.9%），"
          "**Δ +14.6%，2×CV 带 1.9%** ⇒ 方向与④（少专家⇒更快）**相反**。"
          "**再做 Zipf 对照**（同词表、同词数、按 1/rank 抽样：路由集中但**无长重复**）："
          "**1531 ms/ktok（CV 0.5%）vs hi 1539 ms/ktok（剔除被 prompt-cache 污染的 hi#0，0.38 s）⇒ Δ −0.5%，带内**。"
          "⇒ **+14.6% 不是「路由集中/并行度」造成的**，而是**「重复」本身**：候选④（tile 填充地板）按此操作化**不成立**；"
          "**新候选⑤：n-gram/重复相关的主机侧开销**（投机/ lookahead 一类的重复感知路径），成本 ∝ 重复度。"
          "**边界**：`lo` 是极端重复（同一 18 词 ×108 次），真实提示极少这么规整；`hi#0` 因命中 prompt cache 被剔除（诚实标注）。"
          "**顺带**：本轮我自己写错过一次——词表 19 个词给了 18 个权重（`random.choices` 直接 `ValueError`），已修。")

SEC = """
**26. ④ 被自己的实验否掉，但顺手挖出一个新候选——问题不在专家，在「重复」。**
上一轮我把 ④ 操作化成「重复文本 ⇒ 参与专家少 ⇒ 更快」。按 n=5、交错、长度对齐重做，**方向反了**：

| 组 | 构造 | ms/ktok | CV |
|---|---|---|---|
| `hi` | 19 词随机词序 | **1548** | 1.0% |
| `lo` | 同一 18 词短语重复 108 次 | **1774** | 0.9% |

**Δ = +14.6%，2×CV 带 = 1.9%** ⇒ 重复文本**更慢**。④ 按这个操作化**不成立**。

**再做一刀把「路由」和「重复」分开**：同样 19 个词、同样 1944 词，改成按 **Zipf(1/rank)** 抽样——
路由同样集中（少数词占多数），但**没有长的重复片段**：

| 组 | 构造 | ms/ktok | CV |
|---|---|---|---|
| `zipf` | Zipf 倾斜、无长重复 | **1531** | 0.5% |
| `hi`（剔 #0） | 均匀随机 | **1539** | 0.6% |

**Δ = −0.5%，带内不可分辨。**

⇒ **结论：路由集中本身对 prefill 没有可分辨影响；那 +14.6% 是「重复」带来的**，与专家数/并行度无关。
候选④（tile 填充地板）在这条路径上**没有得到支持**；新候选 **⑤：n-gram / 重复感知的主机侧开销**（成本 ∝ 重复度）。

**边界（都摆出来）**
- `lo` 是**极端重复**（同一 18 词 ×108），真实提示极少这么规整 ⇒ 这 14.6% 不能直接外推到日常流量。
- `hi#0` **命中 prompt cache**（0.38 s / 132 ms/ktok），是污染样本，**已剔除**；不剔的话 CV 会飙到 50% 并淹没结论。
- 本轮我自己还写错过一次：词表 **19** 个词却给了 **18** 个权重，`random.choices` 当场 `ValueError`——修了才跑通。

**下一步（零停机）**：⑤ 可以用 `--spec` 关掉投机解码再测同一批 `lo` 提示——若 14.6% 消失，⑤ 成立；
若不消失，则要怀疑分词器/预处理对重复的处理。**我仍不把⑤写成结论，它是现在唯一活着的候选。**
"""

PLAN_ADD = """
**补充 13（同日，④ 否 + ⑤ 立）**：n=5 交错、长度对齐 ⇒ `hi`（随机词序）**1548 ms/ktok CV 1.0%** vs `lo`（同短语 ×108）**1774 CV 0.9%**，**Δ +14.6%（带 1.9%）方向与④相反**；Zipf 对照（集中但无长重复）**1531 vs hi 1539，Δ −0.5% 带内** ⇒ **+14.6% 来自「重复」不是「路由集中」**，④ 按此操作化不成立。**新候选⑤：n-gram/重复的主机侧开销**。边界：`lo` 是极端重复、`hi#0` 命中 prompt cache 已剔除。下一步：`--spec` 关投机再测同一批 `lo`。
"""

MEMSEC = """
- 04:5x **④ 否、⑤ 立**：n=5 交错 ⇒ `hi` 1548 ms/ktok（CV 1.0%）vs `lo`（同短语×108）1774（CV 0.9%），**Δ +14.6%（带 1.9%）方向相反**；Zipf 对照（集中无长重复）1531 vs 1539 **Δ −0.5% 带内** ⇒ **+14.6% 是「重复」不是「路由集中」**，④（tile 填充）按此操作化不成立；**新候选⑤ = n-gram/重复的主机侧开销**。边界：`lo` 极端重复、`hi#0` 命中 prompt cache 已剔除（不剔 CV 飙 50%）。自写 bug：19 词给 18 权重 → ValueError。下一步 `--spec` 关投机复测。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "候选④ 的操作化被否" in t:
        return "P418 已记④否"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加④否/⑤立"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "26. ④ 被自己的实验否掉" in t:
        return "§26 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§26 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 13（同日，④ 否 + ⑤ 立）" in t:
        return "方案补充 13 已存在"
    anchor = "**补充 12（同日，候选① 否）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 13 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "④ 否、⑤ 立" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
