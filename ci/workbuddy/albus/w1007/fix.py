#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1007: remediate the audit outputs and restructure the plan around one source of truth.

Two jobs:
  1. audit outputs -- the index's own count for AUDIT24 disagrees with the audit file, and a
     residual question that audits keep carrying (R15' = the ring depth / prefetch of wait copy)
     has no ledger row at all, so it is invisible to every gate.
  2. the plan -- 1204 lines with three copies of the same numbers, two execution-order tables
     (one explicitly "do not use"), and no single block that says what is true today.  Every
     round re-derives it, which is how 1.91x survived five rounds.

After this: one 0.1 fact block, one queue, one appendix of retired numbers, everything else
points at them.
"""
import io
import os
import re

W = r"D:/workbuddy_space/strata_ws"
PLAN = os.path.join(W, "deploy/W832_OPT_PLAN_V2.md")
PROG = os.path.join(W, "deploy/PROGRESS.tsv")
IDX = os.path.join(W, "deploy/AUDIT_INDEX.md")


def rd(p):
    return io.open(p, encoding="utf-8").read()


def wr(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


# ---------------------------------------------------------------- 1. audit index count
idx = rd(IDX)
old_row = ("| **AUDIT24** | **W900–W951（50 件，全部首次被审）**：2 P0（W909 专家格式误判 / W832 方案落后于账本）、"
           "16 P1、12 P2、4 需复核；**A 级复跑 3 次**（PMC 67.3%、pack 字节、生产 804 tok/s）+ 外网核对 2 次 | "
           "**2** | **15** | **12** | **0** |")
assert old_row in idx, "AUDIT24 row shape changed"
idx = idx.replace(old_row, old_row.replace("| **2** | **15** | **12** | **0** |",
                                           "| **2** | **16** | **12** | **0** |"))
# 合计 must be the arithmetic sum of the rows, not a hand-kept number
nums = []
for line in idx.splitlines():
    m = re.match(r"\|\s*\**\s*AUDIT\d+\s*\**\s*\|(.*)$", line)
    if not m:
        continue
    cells = [c.strip().strip("*").strip() for c in m.group(1).split("|")]
    # cells: 覆盖 | P0 | P1 | P2 | P3 | 文件
    if len(cells) >= 5 and all(re.fullmatch(r"\d+", c) for c in cells[1:5]):
        nums.append(tuple(int(c) for c in cells[1:5]))
tot = tuple(sum(c) for c in zip(*nums)) if nums else (0, 0, 0, 0)
idx = re.sub(r"\| \*\*合计\*\* \| \*\*W776–W1005 \+ 方案本体\*\* \| \*\*\d+\*\* \| \*\*\d+\*\* \| \*\*\d+\*\* \| \*\*\d+\*\* \|",
             "| **合计** | **W776–W1005 + 方案本体**（%d 件） | **%d** | **%d** | **%d** | **%d** |"
             % (len(nums), tot[0], tot[1], tot[2], tot[3]), idx)
wr(IDX, idx)
print("index: AUDIT24 P1 15->16, 合计 = %s over %d audits" % (tot, len(nums)))

# ---------------------------------------------------------------- 2. plan
plan = rd(PLAN)

# 2a. one fact block, right under the one-rule paragraph
FACT = """
### 0.1 现行事实（**唯一来源**；其余章节一律指回这里，不再各自复述数字）

> `W1007` 起：这一段是唯一可以写"现在是多少"的地方。别的章节写数字只许两种形式——
> 指向本段，或写明"某轮实测"并给出证据件。**同一数字在方案里出现三处**是 1.91× 活过五轮的机制。

| 项 | 现值 | 证据 / 门 |
|---|---|---|
| 生产容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101` | `docker inspect`；八字段每轮首段 |
| 引擎 md5 / 大小 | `eea5ea3749ad54b124330386605a18bc` / 44,908,992 B（`strata-0.1.56-090`） | disk = build = running 三方 |
| config md5 / args / env | `e62685e6ff21d9e2b60c1cd622fd5a67` / 37 / 9 | 同上 |
| 2K prefill 相位 | GPU **3191 ms**；gu 816、down 510、dequant **161（5.0%）**、wait copy **37（1.2%）**、host grouping **91（2.9%）** | `ci/prefill_phases/PREFILL_PHASES.tsv`（n=3 冷 prompt）+ `phases.py --check` |
| 2K 相对 16K 的每 token 成本 | 整条 **1.23×**；gate/up **1.57×**、down **1.52×** | 同上（16K = 16375 tok / 20318 ms） |
| 专家权重类型 | gu = Q4_K/Q5_K @[1280,2560]；down = Q5_1/Q8_0 @[2560,640] | `native_experts.txt`（pack 清单） |
| 进度分母 | 232 条 / 已结 153 / 65.9% | `deploy/PROGRESS.tsv`（唯一分母） |
| **唯一队列** | **R95（外围/host 侧）→ R94 → R91 → R89 → R46 → R49 → R50 → R98** | 本节 + `§6.5` 各回写块 |
| 权威件（六件） | `W832`(本件) · `PROGRESS.tsv` · `params/PARAM_REGISTER.tsv` · `ID_MAP.tsv` · `AUDIT_INDEX.md` · 最新审计件 | `albus/w1003/mirror_check.py` 逐字节 |
| 已退役数字 | 见 **附录 A** | `tools/plan_retired.py` 拦「以现行事实出现」 |

"""
anchor = "| 文件 | 角色 | 能不能改队列 |"
assert anchor in plan
plan = plan.replace(anchor, FACT.lstrip("\n") + anchor, 1)

# 2b. the superseded execution-order table -> a pointer (one queue only)
lines = plan.split("\n")
start = next(i for i, l in enumerate(lines) if l.startswith("### ~~当前唯一执行序~~"))
end = next(i for i in range(start + 1, len(lines)) if re.match(r"^#{2,3} ", lines[i]))
old_block = "\n".join(lines[start:end])
new_block = """### ~~当前唯一执行序（V3.9）~~ → 已并入 §0.1

> `W1007` 删除：这张表与 §6.5 的「新执行序」是同一件事的两份，其中一份的第 1 序（R97）当天就解散了。
> **队列只在 §0.1 维护一条**；历史顺序见 `§6.5 回写 · W1003`。原表 12 行的内容已全部落在
> `PROGRESS.tsv` 的对应条目里，不再在这里留副本。
"""
plan = plan.replace(old_block, new_block, 1)

# 2c. appendix A: every retired figure, one table
APP = """

## 附录 A · 退役数字表（**只有这里能写旧值**）

> 规则（`tools/plan_retired.py` 强制）：这些数字只允许以删除线或在本表内出现；出现在任何"事实表行"即 FAIL。
> 每一行都要写清「谁判的、换成什么」，否则下一个人还会引旧值。

| 退役值 | 曾用于 | 何时退役 | 现应写 |
|---|---|---|---|
| gate/up **1.91×**、down **1.87×** | R95（2K 相对 16K 的每 token 成本） | `W1005` | **1.57× / 1.52×**（`PREFILL_PHASES.tsv`） |
| `dequant` **3.9×（266 ms）** | R95 的"每 token 惩罚" | `W1005` | dequant 是**每 chunk 固定量**：2K **161 ms**、8K 525、16K 491 |
| `wait copy` **14×（170 ms）** | R95 同上 | `W1005` | **37 ms（1.2%）**（issuer 线程 + 按组 gather 之后） |
| `dequant` 8–18%、`wait copy` 7–15% | 性价比排序 | `W1005` | 分母不同：前者 5.0%、后者 1.2% |
| 「#22174 双 3090 **+17%**」 | 说明 stream-k 的收益 | `W1006` | #22174 是**关掉** stream-k 后 **+9.67%**（2597→2848）；约 17% 属 2×4090 的另一处报道 |
| 「#31188 DGX Spark **+17.2%**」 | R96 的立项理由 | `W1006` | **PR 内无性能栏**，两处独立报道称无法核实 ⇒ 只能写「作者称」 |
| 专家字节「**88.6%**」 | R86 的分母 | `W944` / `AUDIT24 A24-3` | Q5_1 占专家总字节 **35%**、down 内 **86%** |
| 「MMQ 五扇门全关」 | 方案 §6.5 旧横幅 | `W943`→`W947` | R60/R63 **OPEN**、R84 **INFLIGHT**（`AUDIT24 A24-2`） |
"""
plan = plan.rstrip("\n") + APP
wr(PLAN, plan)
print("plan: 0.1 fact block + one queue + appendix A")

# ---------------------------------------------------------------- 3. ledger: R98 for the residual
p = rd(PROG)
lines = p.split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID, ST = head.index("id"), head.index("status")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
new_rows = []
if "R98" not in have:
    new_rows.append("\t".join([
        "B2数值债", "R98",
        "wait copy 的预取深度：ring 槽数与 issuer 的领先量（`STRATA_PREFILL_RING` / `STREAM_AHEAD` / `STAGER_RING` 一族）",
        "W1007", "count", "1", "0", "OPEN",
        "**W1007 立**：`AUDIT_INDEX` 的「仍未结清」表里挂着这条，写法是 `R15'`——**账本里没有这个号**，"
        "所以 `plan_lint`/`ledger_lint` 都看不见它，等于一条永久免检的待办。`R15`（pinned ring）已 DONE，"
        "剩下的是深度/预取：`W1005` 实测 wait copy 只剩 37 ms（1.2%）⇒ **先量再决定**，"
        "判据：2K 档 wait copy < 20 ms 或端到端 ≥2×CV 才动，否则关。",
        "deploy/W832_OPT_PLAN_V2.md §6.2 新32"]))
if new_rows:
    lines += new_rows
    wr(PROG, "\n".join(lines) + "\n")
print("ledger: +R98" if new_rows else "ledger: R98 exists")
