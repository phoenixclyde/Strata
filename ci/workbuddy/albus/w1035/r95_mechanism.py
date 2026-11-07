"""W1035 第 23 段：固定项 665 ms 的三个候选机制 + 判别实验（把窗口变成可证伪的测试）。

同时撤回：用 round(n/1000) 给旧 campaign 分档是错的（2450/2509 被切成两档），那次拟合不可用。
"""
import io
import os
import shutil

REP = "albus/w1035/reply.md"
PROG = "deploy/PROGRESS.tsv"
PLAN = "deploy/W832_OPT_PLAN_V2.md"
MEM = ".workbuddy/memory/2026-11-07.md"


def backup(p):
    b = p + ".bak_w1035s"
    if not os.path.exists(b):
        shutil.copyfile(p, b)


APPEND = (" **【W1035 机制候选（P418 续）】**：固定项 665 ms 在 gate/up + down 里，三个候选与判别法——"
          "① **权重搬运**（PCIe）：2K prefill 借 **3.49 GiB**；链路实测 `16.0 GT/s PCIe x16`（PCIe 4.0，非降速）"
          "⇒ 20 GB/s 时 **187 ms**、10 GB/s 时 **375 ms**、5.6 GB/s 时 **750 ms**；b=665 对应有效 **~5.6 GB/s**，"
          "对 4.0 x16 偏低、本身可疑；判别=冷/热 expert-cache 对照，预测 b 随借用字节线性。"
          "② **权重反量化/重排**（算力）：预测 b 随「参与专家的唯一数」变、与 PCIe 无关；判别=改 `--expert-cache` 大小。"
          "③ **调度/建表**：预测 b 随 层数×tile 数 线性、与专家唯一数无关；判别=`STRATA_MMQ_DEBUG_J=1` 数 launch 数。"
          "**反证**：`wait copy` 只有 **36 ms**（不随长度变），若 665 ms 是显式拷贝，它该更贵 ⇒ 要么搬运不记在这一列，"
          "要么机制不是搬运。**下一手**：三者用一个 2K 窗口分开（每个 3 min 级），先把「搬运 vs 反量化」判掉。")

SEC = """
**23. 固定项 665 ms 的三个候选机制——先把窗口变成可证伪的测试，再去停机。**
上一条的结论是「`R95` 的 1.57× 是每次调用的固定开销，且 82% 在两个 GEMM 相位里」。**但我没说是哪来的**，
所以现在补三件事：把候选列成可分辨的，把每个的预测值算出来，再决定窗口里测哪一个。

**先撤回一处**：我想用「旧 campaign 更慢 ⇒ 固定项与状态相关」来旁证，结果**分档方法本身就错**——
按 `round(n/1000)` 分组把 2450 和 2509 切成了两档，拟合退化（墙钟 b=579 ms 却拟合出 4 档），
**那次对比作废，不作为证据**。

**PCIe 实况（sysfs，非估算）**：GPU `0000:05:00.0` = **`16.0 GT/s` × 16**，与 `max_link_speed` 一致
⇒ 满速 PCIe 4.0 x16，没有降速/降宽。

| 候选 | 机制 | 判别实验 | 若成立的预测 |
|---|---|---|---|
| ① 权重搬运 | 每次 prefill 借 **3.49 GiB** 专家到卡上 | 冷 / 热 expert-cache 对照 | b 随借用字节线性 |
| ② 反量化/重排 | 每 prefill 把参与的专家权重重新 dequant/pack | 改 `--expert-cache` 大小（改唯一专家数） | b 随**唯一专家数**变，与 PCIe 无关 |
| ③ 调度/建表 | 层 × tile 的建表与派发 | `STRATA_MMQ_DEBUG_J=1` 数 launch | b 随 **层数×tile 数** 线性，与专家唯一数无关 |

**搬运候选的定量底**：3.49 GiB 在 20 GB/s 下 **187 ms**、10 GB/s 下 **375 ms**、5.6 GB/s 下 **750 ms**。
b=665 ms ⟹ 有效带宽 **~5.6 GB/s**。对 PCIe 4.0 x16 这个数**偏低**（正常 H2D 能到 20 GB/s 量级），
所以要么是**大量小拷贝/未走 pinned 直通**，要么**根本不是搬运**。这条怀疑必须先测掉。

**一条反向证据（必须摆出来）**：`wait copy` 只有 **36 ms** 且不随长度变。若 665 ms 真是显式拷贝，
这一列理应更贵。两种解释：搬运不计在 `wait copy`（比如算进 gemm 相位），或机制不是搬运。
**在没测之前，我不选边。**

**窗口设计（三个 3 分钟级窗口，按信息量排序）**
1. `--expert-cache` 1473（=3.49 GiB 恰好）vs `auto`：同 2K 提示，看 b 是否随借用字节变 ⇒ 判①/②。
2. 同一提示连打两次（第二次必然全命中）：b 是否塌到 ~0 ⇒ 直接判「是否与缓存状态相关」。
3. `STRATA_MMQ_DEBUG_J=1`：数 launch 数，检查 665 ms ÷ launch 数 是否落在单次 launch 的合理量级 ⇒ 判③。

**为什么先算再停机**：如果窗口只是"去看看"，跑完还是不知道测什么；现在每个候选都带预测值，
窗口跑完要么被证实、要么被证伪——**这轮之前的毛病正是"停机测了但没判据"**。
"""

PLAN_ADD = """
**补充 10（同日，固定项机制候选）**：665 ms 在 gate/up+down 的固定项，三候选与判别——① 权重搬运（2K 借 **3.49 GiB**；链路 `16.0 GT/s x16` PCIe 4.0 非降速；20/10/5.6 GB/s ⇒ **187/375/750 ms**，b=665 对应有效 **~5.6 GB/s**，偏低可疑）；② 反量化/重排（随唯一专家数变）；③ 调度/建表（随层数×tile 数变）。**反证**：`wait copy` 仅 36 ms 且不随长度变 ⇒ 搬运不记在该列，或机制不是搬运，未测不选边。窗口三步：`--expert-cache 1473` vs `auto` / 同提示连打两次 / `STRATA_MMQ_DEBUG_J=1` 数 launch。**另撤回**：用 `round(n/1000)` 分档比较两 campaign 是错的（2450/2509 被切两档），该拟合作废。
"""

MEMSEC = """
- 04:4x **固定项 665 ms 的机制候选**（P418 续）：① 权重搬运（借 3.49 GiB，PCIe **16 GT/s x16** 实测满速；20/10/5.6 GB/s ⇒ 187/375/750 ms，b=665 ⇒ 有效 ~5.6 GB/s 偏低可疑）② 反量化/重排（随唯一专家数）③ 调度/建表（随层×tile）。**反证：`wait copy` 仅 36 ms 不随长度变** ⇒ 未测不选边。窗口三步：expert-cache 1473 vs auto / 同提示连打两次 / `STRATA_MMQ_DEBUG_J=1` 数 launch。**撤回**：`round(n/1000)` 分档比较两 campaign 是错的（2450/2509 被切两档），拟合作废。
"""


def append_p418():
    t = io.open(PROG, encoding="utf-8").read()
    if "机制候选（P418 续）" in t:
        return "P418 续已存在"
    backup(PROG)
    lines = t.rstrip("\n").split("\n")
    for i, l in enumerate(lines):
        f = l.split("\t")
        if f[1:2] == ["P418"]:
            f[9] = (f[9].rstrip() + APPEND).strip()
            lines[i] = "\t".join(f)
            io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
            return "P418 已追加机制候选"
    return "P418 未找到"


def add_section():
    t = io.open(REP, encoding="utf-8").read()
    if "23. 固定项 665 ms 的三个候选机制" in t:
        return "§23 已存在"
    backup(REP)
    io.open(REP, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n" + SEC)
    return "§23 已写"


def add_plan():
    t = io.open(PLAN, encoding="utf-8").read()
    if "补充 10（同日，固定项机制候选）" in t:
        return "方案补充 10 已存在"
    anchor = "**下一手需停机窗口拆「权重搬运 vs 调度/建表」**"
    i = t.find(anchor)
    if i < 0:
        return "锚点未找到"
    j = t.find("。", i) + 1
    backup(PLAN)
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(t[:j] + "\n" + PLAN_ADD + t[j:])
    return "方案补充 10 已加"


def add_mem():
    if not os.path.isfile(MEM):
        return "记忆文件不存在"
    t = io.open(MEM, encoding="utf-8").read()
    if "固定项 665 ms 的机制候选" in t:
        return "记忆已含"
    io.open(MEM, "a", encoding="utf-8", newline="\n").write(MEMSEC)
    return "记忆已追加"


if __name__ == "__main__":
    for fn in (append_p418, add_section, add_plan, add_mem):
        print(fn.__name__, "->", fn())
