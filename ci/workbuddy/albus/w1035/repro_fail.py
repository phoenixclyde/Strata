"""W1035 第 27 段：+14.6% 未复现 → 撤回；④⑤ 均无支持；R95 剩下的是"机制未定"。

这是本轮最重要的诚实记录：一个 CV 1% 的超带结果，在更严格的设计下消失了。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035x"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 复现失败 → 撤回 +14.6%】**：同设计（n=5、交错、每轮换排列以避开 prompt cache）重做，"
          "`ordered`（同一排列重复 ×108）**1753 ms/ktok（CV 2.8%）** vs `shuffled`（同词频、块内随机）"
          "**1697 ms/ktok（CV 10.2%）** ⇒ **Δ +3.3%，2×CV 带 20.5% ⇒ 带内，不可分辨**。"
          "⇒ **上一轮那个 +14.6%（带 1.9%）没复现**，按 B7 判据**撤回，不得再引用**。"
          "**⑤（n-gram/重复主机侧开销）因此也没有证据支持**；加上先前被否的 ①（PCIe 仅 0.1–1.2%）与"
          "③（6.9 ms/launch 高三个数量级），以及**未获支持**的 ④（tile 填充）——"
          "**四个候选全部出局，`R95` 的固定项机制仍未定**。"
          "**稳的部分**（仍然成立）：固定项确实存在且 82% 在两个 GEMM 相位（gate/up 416 ms、down 249 ms、"
          "墙钟 b=842 ms，各相位固定项之和 807 ms 与墙钟差 4%）。"
          "**下一手的正确形态**：不再用总墙钟推断，改用相位探针（`ci/prefill_phases/w1005_probe.py`）"
          "直接读 GEMM 相位内部拆分；那需要窗口（探针要独占引擎）。")

SEC = """
**27. 复现失败：`+14.6%` 撤回，四个候选全部出局，`R95` 停到「机制未定」。**
上一轮我有个 CV 1.0% / 0.9%、带 1.9% 的超带结果（重复文本慢 14.6%），并据此立了候选⑤。
本轮按同一设计（n=5、交错）重做，只多改了一处——**每轮换一个排列，避开 prompt cache**：

| 组 | 构造 | ms/ktok | CV |
|---|---|---|---|
| `ordered` | 同一排列重复 ×108 | **1753** | 2.8% |
| `shuffled` | 同词频、块内随机 | **1697** | 10.2% |

**Δ = +3.3%，2×CV 带 = 20.5% ⇒ 带内，不可分辨。**

**⇒ 那个 +14.6% 没复现，按 `B7`（结论必须能被重复实测）撤回，此后不得引用。**
上一轮上一版还有个更弱的设计（`ordered` 内容完全相同 ⇒ 从第 2 次起全命中 prompt cache，0.25 s），
我当时剔了 #0 就继续用，**这本身也是错的**——正确做法是换内容重跑，而不是剔除污染样本后凑 n。

**四个候选现在全部出局**
| 候选 | 状态 | 证据 |
|---|---|---|
| ① 权重搬运 | **否** | PCIe 占比 0.1–1.2%，折 ~1.5 ms vs 665 ms |
| ② 反量化/重排 | **未测**（不排除，但 pack 已是量化态，先验低） | — |
| ③ 调度/建表 | **否** | 1 launch/调用，6.9 ms 高三个数量级 |
| ④ tile 填充地板 | **未获支持** | 操作化后方向相反，且未复现 |
| ⑤ n-gram 重复开销 | **未获支持** | +14.6% 未复现；`ngram_rows` 是 PLE 行选择、重复应更快 |

**稳的部分没变**：固定项存在，**82% 在两个 GEMM 相位**（gate/up 416 ms、down 249 ms；各相位固定项之和 807 ms
与墙钟 `b=842 ms` 差 4%）。

**下一手换形态**：不再拿总墙钟倒推机制，改用相位探针 `ci/prefill_phases/w1005_probe.py` 直接读 GEMM 相位内部，
并且**同一 session 内交错、相位级重复**。它要独占引擎 ⇒ 需要窗口。**在那之前 `R95` 的状态就是"固定项定位完成、机制未定"，
不再产出候选。**

**这一轮的教训（写进纪律候选）**：一个 CV 1% 的超带结果也可能是假的——**除非换设计复现一次**。
我这轮三次栽在同一个地方（污染样本剔除后凑 n、长度差 6%、内容相同被缓存），
说明**"实验设计"本身需要门**：n≥5、内容全新、长度差 ≤1%、交错、且**必须有一次独立复现**。
"""

PLAN_ADD = """
**补充 14（同日，复现失败与撤回）**：`+14.6%` **未复现**——同设计 n=5 交错、每轮换排列避缓存 ⇒ `ordered` 1753（CV 2.8%）vs `shuffled` 1697（CV 10.2%），**Δ +3.3%、带 20.5%、带内** ⇒ **撤回，不得引用**。**⑤ 因此无支持**；连同 ①（PCIe 0.1–1.2%）与 ③（6.9 ms/launch）被否、④ 未获支持 ⇒ **四候选全部出局，`R95` 停在"固定项定位完成（82% 在两 GEMM 相位、b=842 ms）、机制未定"**。下一手改为相位探针（`w1005_probe.py`，需窗口）。**纪律候选：实验设计本身要门——n≥5 / 内容全新 / 长度差≤1% / 交错 / 必须独立复现一次。**
"""

MEMSEC = """
- 05:0x **复现失败，撤回 +14.6%**：n=5 交错、每轮换排列 ⇒ ordered 1753（CV 2.8%）vs shuffled 1697（CV 10.2%），**Δ +3.3%、带 20.5% 带内** ⇒ 上一轮那个超带结果**没复现**，按 B7 撤回。⑤ 无支持；①（PCIe 0.1–1.2%）③（6.9 ms/launch）被否、④ 未获支持 ⇒ **四候选全出局，R95 停在"固定项定位完成、机制未定"**。稳的部分：固定项 82% 在两 GEMM 相位（416/249 ms，墙钟 b=842）。**纪律候选：n≥5 / 内容全新 / 长度差≤1% / 交错 / 必须独立复现一次。**
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "复现失败 → 撤回 +14.6%" in t:
        return "P418 已记撤回"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加撤回"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "27. 复现失败" in t:
        return "§27 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§27 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 14（同日，复现失败与撤回）" in t:
        return "方案补充 14 已存在"
    anchor = "**补充 13（同日，④ 否 + ⑤ 立）**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("\n\n", i)
    if j < 0:
        j = len(t)
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + "\n" + t[j:])
    return "方案补充 14 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "复现失败，撤回 +14.6%" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
