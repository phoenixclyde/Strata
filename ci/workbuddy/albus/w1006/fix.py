#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1006 audit fixes: the rounds nobody had audited (W898/W899, W986-W1005) and what they left.

Each replacement asserts its anchor.  Run from the workspace root, then sync + gates.
"""
import io
import os
import sys

W = r"D:/workbuddy_space/strata_ws"
PLAN = os.path.join(W, "deploy/W832_OPT_PLAN_V2.md")
PROG = os.path.join(W, "deploy/PROGRESS.tsv")
IDX = os.path.join(W, "deploy/AUDIT_INDEX.md")


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def sub(s, old, new, count=1):
    assert old in s, "anchor missing: %s" % old[:60]
    return s.replace(old, new, count)


plan = rd(PLAN)

# F8a: the priority table still quotes the retired ratios
plan = sub(
    plan,
    "| 5 | R95 小批 GEMM | 2K 的 gate/up 1.91×；J=64 是 K-quant 下限 |",
    "| 5 | R95 小批 GEMM | 2K 的 gate/up **1.57×**（`W1005` 重测；~~1.91×~~ 是跨 build 日志）；J=64 是 K-quant 下限 |")

# F8b: the execution-order table, same disease
plan = sub(
    plan,
    "| 1 | **R95 小批 GEMM** | 2K 的 gate/up 1.91×、down 1.87×，占 68%；R95 内部已拆出 dequant 3.9×、wait copy 14× |",
    "| 1 | **R95 小批 GEMM** | 2K 的 gate/up **1.57×**、down **1.52×**（`W1005`；~~1.91/1.87~~）；dequant **161 ms（5.0%）**、wait copy **37 ms（1.2%）**（~~3.9×/14×~~ 是 per-token 归一化造的假惩罚） |")

# F6: #31188's 17.2% is not in the PR
plan = sub(
    plan,
    "2. **上游 2026 两笔融合对 prefill 无效**（#29948 稠密 +7.1%、#31188 MoE DGX Spark +17.2% / 5090 +5.7%）：",
    "2. **上游 2026 两笔融合对 prefill 无效**（#29948 稠密 +7.1%；#31188 MoE，**PR 内无性能栏**，`W1006` 外网复核两处独立报道均写「无法核实 17.2%」——引用它时只能说「作者称」）：")

# F5: #22174 is the opposite direction and a different number
plan = sub(
    plan,
    "**这一条拦下了一个差点做的错事**：上游 MoE stream-k（#22174，双 3090 +17%）的收益前提是核内 wave 量化，\n而本地 kernel 已经不量化了 —— 按上游结论去移植会白做一轮。",
    "**这一条拦下了一个差点做的错事**：上游 MoE 的同类收益前提是核内 wave 量化。`W1006` 外网复核更正两处——"
    "#22174 的实测是 **关掉** stream-k 后双 3090 **+9.67%**（2597→2848 t/s，单卡仅 0.073%），即那一轮的赢法是"
    "**用 tiling 取代 stream-k**，不是加 stream-k；约 17% 是另一处 2×4090 的报道。我们的 kernel 在 192→1024 行"
    "已不平坦区劣化，两条路都不对症 ⇒ 移植会白做一轮，且**连方向都不该照抄**。")

# F6b: the "dequant 8-18% / wait copy 7-15%" split is superseded too
plan = sub(
    plan,
    "3. **性价比排序（每轮对照用）**：dequant 8–18% 与 wait copy 7–15%（R95 内部拆分，机制已清、不动 kernel）",
    "3. **性价比排序（每轮对照用）**：~~dequant 8–18% 与 wait copy 7–15%~~（`W1005` 实测口径不同：dequant **161 ms = prefill 的 5.0%**、wait copy **37 ms = 1.2%**，机制已清、不动 kernel）")

wr(PLAN, plan)
print("plan: 5 replacements")

# ---------------------------------------------------------------- PROGRESS
p = rd(PROG)
lines = p.split("\n")
h = lines[0].split("\t") if lines[0].startswith("#") else None
# find the header row (first non-comment)
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
II, IT, ST, NO = head.index("id"), head.index("item"), head.index("status"), head.index("note")

for i, l in enumerate(lines):
    if l.count("\t") < 9:
        continue
    c = l.split("\t")
    if c[II] == "R95":
        c[IT] = ("小批 GEMM 效率（`W1005` 重写）：2K 对 16K 的每 token 成本 gate/up **1.57×**、down **1.52×**、"
                 "整条 prefill **1.23×**；dequant 161 ms = 5.0%、wait copy 37 ms = 1.2%（~~1.9×/3.9×/14×~~）")
        c[NO] = c[NO] + (" 【W1005 重写 2026-11-05 23:0x】**三条候选全部出局**：A 几何（W992）；B 上游 GCN 的 "
                         "MUL_MAT_ID→MMVQ 阈值是 **4 行**（`mmvq.cu:190`），我们 p50=331；C 天花板 5.0% 且 DIRECT 需 TAB、"
                         "ROUTED_STREAM 1K −7.6%。**残余 1.57× 不在 MMQ 核内**（WIDTH_SWEEP 192→1024 行 0.0033 ms/row 平坦）"
                         "⇒ 下一手量 host/launch 侧，不移植内核。表在 `ci/prefill_phases/PREFILL_PHASES.tsv`。")
        lines[i] = "\t".join(c)
    elif c[II] == "R88":
        c[ST] = "DONE_NEG"
        c[NO] = c[NO] + (" 【W1006 判否 2026-11-05 23:3x】假设被自己的实测证伪：`W990` 的 GPU timeline 与 wall 只差 "
                         "**15 ms**（2K）/122 ms（16K）⇒ 没有可重叠的缝；`W983` 量的借用量与 pcie-frac 双向无效。"
                         "「首块串行」不存在，工作转 R95（小批 GEMM）。保留条目作历史，计 DONE_NEG。")
        lines[i] = "\t".join(c)
    elif c[II] == "R96":
        c[ST] = "NA"
        c[NO] = c[NO] + (" 【W1006 与方案对齐 2026-11-05 23:3x】方案 新31 早已判 **N/A**（`W1003`：我们 gu 是 "
                         "`prefill.cpp:5300` 的一次 1280 行调用，上游省的是第二次 launch），账本却仍 OPEN ⇒ 分母不一致，改 NA。")
        lines[i] = "\t".join(c)

NEW = [
    ("B6判定探针", "P299", "未审区间定位：审计索引停在 AUDIT24，AUDIT25 未登记；真未审 = W898/W899 + W986–W1005",
     "W1006", "DONE",
     "**W1006 立**：`AUDIT_INDEX.md` 覆盖表只到 AUDIT24（W776–W951），而 `AUDIT25_W952_W985.md` 已存在却没登记 ⇒ 用索引判「哪些没审」必错。逐轮核：W855/W884/W885 无此轮；W854 只有旁证；**W898/W899 落在 AUDIT23(–897) 与 AUDIT24(900–) 的缝里**；W986–W1005 共 20 轮从未被审。合计 22 轮。",
     "deploy/AUDIT26_W898_W1005.md"),
    ("B6判定探针", "P300", "W898/W899 审计：口径变更与 R54 判否均已上账、有落点（0 缺陷）",
     "W1006", "DONE",
     "**W1006 立**：W898（只做单流 ⇒ R57 WITHDRAWN、R54 挂起、§0.2 三条重写）与 W899（R54 DONE_NEG、撤回「文本 sha 相同=无差异」的判据）在账本里分别为 R57/R54 且状态一致，方案里 R52/R54/R55/R57 各 3–5 处落点。**唯一遗留是它们从未被任何审计件引用**，补进 AUDIT26 覆盖表。",
     "deploy/AUDIT26_W898_W1005.md"),
    ("B6判定探针", "P301", "W986–W1005 审计：账本口径三处不一致（R95 item / R88 OPEN / R96 OPEN）",
     "W1006", "DONE",
     "**W1006 立**：①R95 的 item 行仍写 1.9×/3.9×/14×（W1005 只改了方案，没改账本行）；②R88 状态 OPEN 但假设已被 W990 证伪（缝隙 15 ms）；③R96 状态 OPEN 而方案 新31 早已 N/A。三处都让**分母和叙述互相矛盾**。已分别改 item / DONE_NEG / NA。",
     "deploy/W832_OPT_PLAN_V2.md §6.2 新30"),
    ("B4上游移植", "P302", "外网复核更正两条上游数字：#22174 是「关掉 stream-k +9.67%」，#31188 PR 内无性能栏",
     "W1006", "DONE",
     "**W1006 立**：①#22174（nisparks）实测**禁用** MMQ stream-k 后双 3090 **+9.67%**（2597→2848 t/s）、单卡 0.073%；#22298 是用 fastdiv+tiling 取代 stream-k ⇒ 方案里「#22174，双 3090 +17%」数字与方向**都错**（17% 属 2×4090 的另一处报道）。②#31188 PR 无 benchmark，两处独立报道均称 17.2% 无法核实。结论不变（都不对症），理由已改。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1005"),
    ("B8工程", "P303", "门：审计索引必须随审计更新 + `plan_retired.py` 拦退役数字",
     "W1006", "DONE",
     "**W1006 立**：两类失效都是「同一事实写多处、只改一处」。①AUDIT_INDEX 由 `ci/audit_index.py` 从审计件机械重建并断言每个 AUDIT 件都有一行（缺即 FAIL）；②`ci/plan_retired.py` 维护退役数字表（1.91×/1.87×/3.9×/14×…），在方案里出现即 FAIL，负向自测 3/3。",
     "ci/plan_retired.py"),
]
add = []
cur = set()
for l in lines:
    if l.count("\t") >= 9:
        cur.add(l.split("\t")[1])
for blk, pid, item, src, st, note, ref in NEW:
    if pid in cur:
        continue
    add.append("\t".join([blk, pid, item, src, "count", "1", "1", st, note, ref]))
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add
    lines.append("")
wr(PROG, "\n".join(lines))
print("progress: +%d rows, 3 status/item edits" % len(add))

# ---------------------------------------------------------------- AUDIT_INDEX
idx = rd(IDX)
row25 = ("| **AUDIT25** | **W952–W985（34 轮）** | — | — | — | — | `AUDIT25_W952_W985.md` |\n")
row26 = ("| **AUDIT26** | **W898–W899 + W986–W1005（22 轮，全部首次被审）**：3 处账本口径不一致 + 2 条上游数字错（#22174 方向/数字、#31188 无性能栏）；0 P0 | 0 | 3 | 2 | 0 | `AUDIT26_W898_W1005.md` |\n")
anchor = "| **合计** | **W776–W951 + 方案本体** | **34** | **125** | **107** | **7** | — |"
assert anchor in idx
if "AUDIT25" not in idx:
    idx = idx.replace(anchor, row25 + row26 + anchor.replace("**W776–W951 + 方案本体**", "**W776–W1005 + 方案本体**"), 1)
    wr(IDX, idx)
    print("index: AUDIT25 + AUDIT26 rows added")
else:
    print("index: already has AUDIT25")
