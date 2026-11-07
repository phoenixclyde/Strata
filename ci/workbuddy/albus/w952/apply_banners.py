# -*- coding: utf-8 -*-
"""AUDIT24 remediation: insert source banners (idempotent) and correct the numbers that were wrong.

Rule from AUDIT19: a retraction must be written back in three places -- source doc banner,
ledger row, plan table. This script does the doc part; the ledger/plan are edited separately.
"""
import io, os

D = "D:/workbuddy_space/strata_ws/deploy/"
MARK = "【AUDIT24"

BANNERS = {
"W909_DP4A_DOT8_EVIDENCE.md": """
> **【AUDIT24 P0 · 2026-11-04】§5 与 §6.4 的「专家格式」判断作废（算术已复核）**：日志里的
> `MMQ tile: type 20/21/23/8` 是引擎**按类型×J×cap 打的一次性能力表**（实测 4 类型 × 5 cap = **20 行**），
> 不是"本模型专家的类型"。权威来源是 pack 描述符 `native_experts.txt`，且它的**逐专家字节能精确对上算术**：
> `3,072,000 B = Q4_K gate/up 1,843,200 + Q5_1 down 1,228,800`（Q8_0 down 的层则是 3,584,000）。
> ⇒ 专家是 **Q4_K×47 + Q5_K×1（gate/up）／ Q5_1×43 + Q8_0×5（down）**，**没有 IQ 码本类型**。
> ⇒ §6.4「dot8 对 IQ 码本类型连 W4A4 都用不上」**不适用于我们的专家**（线性 4-bit，可用）；
> dot8 的否决结论已由 `W927`（W4A4 下指令减半）推翻，现由 `R84/R91` 在办。
> §1–§4 的指令/二进制/硬件三层证据（sdot8 语义、130,808 条 `v_dot4`、0 条 `v_dot8`）**不受影响**。
""",

"W919_RELEASE_NOTES_READ.md": """
> **【AUDIT24 P1 · 2026-11-04】状态行要撤回一半**：本件把「PLE 表未 mlock」写成**现成的损失**（"不需改一行代码"），
> 但 `W920` 两臂（预热后 rep6–9）实测 **prefill / decode 均在噪声内** ⇒ `R67 = DONE_NEG`：
> 补丁本身是对的，只是在当前 `unlimited` 档**完全静默**。另：本件引用的 0.2.10 release notes 文本当时只落在 `/tmp`，
> 仓库里没有留副本（复现需重下一次）。
""",

"W922_R68_STOP_BOUND.md": """
> **【AUDIT24 P1 · 2026-11-04】§71 的措辞错**：99.72% **低于**上游打补丁后的 99.74%，不是"高于"。
> 正确表述：**与补丁后基本持平（−0.02pp）、远高于补丁前的 98.36%**。结论（没有 6% 可修、不移植）不受影响。
""",

"W923_R61_PMC_FAILED.md": """
> **【AUDIT24 P1 · 2026-11-04】结论外推过宽 + 计数自相矛盾**：
> ①「rocprof 不可用」只对 **`HSA_TOOLS_LIB` 注入**成立 —— `W941/W942` 用 **rocprofv3 当启动器 + 独立可执行自然退出**
> 采到了 PMC（`VALUBusy` 67.1%，本轮复测 67.3%），并据此重开/结题多条；
> ②§2 表列 **3 次**尝试，文末却写「共 4 次重启（2 注入 + 2 恢复）」——以表为准（3 次尝试 + 恢复重启）。
""",

"W924_R58_MMQ_THREE_SEGMENTS.md": """
> **【AUDIT24 P1 · 2026-11-04】分母必须标口径**：「dp4a 占 53.3%」是**整个 mmq-instance 模块**求和
> （多 J、fallback 实例全算），而生产只 dispatch 一个 kernel —— `W943` 换成真 kernel 后是 **30.0%**，
> `R84` 的端到端上限随之从 −3.65% 改判 **−2.05%**。本件「无单段过半」的三段计数经 `W939` 复核仍成立；
> 但凡引用 53.3% 的地方，必须同时写"模块口径"。
""",

"W926_R64_ATTN_INT8.md": """
> **【AUDIT24 P1 · 2026-11-04】三处更正**：①§45 写「占比稳定在 15–19%」，同段实测却是
> 8K **14.8%** / 32K **15.3%** / 99K **15.3%** —— 上界 19% 无出处，应写 **14.8–15.3%**；
> ②§81「最好情况 4–6%」与 §90「3.4–4.3%」自相矛盾，以可复算的 **3.4–4.3%** 为准；
> ③§41 的机制「稀疏 ⇒ O(L×k)」被 `W946` 修正为「每 token 仍扫 2048 个 cell 的候选，再按 `ids` gather」，
> `R89` 已按纪律⑱重开（源码阅读不足以结题）。
""",

"W907_KERNEL_CORRESPONDENCE.md": """
> **【AUDIT24 P1 · 2026-11-04】内核总数与 `W912` 冲突**：本件写「12 个 / 5,220 行」，`W912` 逐文件读后写
> 「19 个 / 5,703 行」。两者都自称逐文件盘点 ⇒ 以 **`W912` 的 19 个**为准（本件漏计了散在 `qwen4exp` 子目录的 7 个）。
> 另：本件「ki 的 FA 可以直接复用」的结论已被 `W912`（逐文件判决）取代。
""",

"W912_KI_PORT_VERDICT.md": """
> **【AUDIT24 P1 · 2026-11-04】§121「领先 37 / 落后 0」是 stale ref 的产物**：当时 `upstream/main` 未 fetch。
> `W917` 实测我们**落后上游 708 条**；`W948` 又指出"三家 fork 比我们旧"的判据也不成立。
> ⇒ 任何以"我们已是 0.2.9 最新"为前提的判断，都要按 `R90` 的基线升级重新评估。
""",

"W913_R59_PRECISION_LEDGER.md": """
> **【AUDIT24 P2 · 2026-11-04】§6 的算术注记**：`arch_defaults.cpp` 那五个 KL
> （0.0011 / 0.0004 / 0.0008 / 0.0026 / 0.0171）是**逐开关单点**，加总 **0.0220**，而整包实测 **0.002005**
> —— 相差 11 倍，**既不能相加，也不能与整包噪声底 0.0032 直接比大小**。本件末段已自述"不能当作整机已验证"，
> 这里补一条算术注记，防止被后续引用成"五个开关总代价 2.2%"。
""",

"W918_UPSTREAM_708_READ.md": """
> **【AUDIT24 P2 · 2026-11-04】§69 的冲突判断已被 `W921` 推翻**：`3cc47f02` 的「需手解 1 处冲突」
> 来自**提交顺序**（先上了别的补丁），先上前置提交后 5 个 hunk **全部干净应用**。R66 的最终判定以 `W921` 的 A/B 为准。
""",

"W940_DOT4_DOT8_AND_PLAN_GAP.md": """
> **【AUDIT24 P1 · 2026-11-04】两条已被推翻，需回写**：
> ①§50「dot8 端到端上限 3.22%，压在噪声门上」只在 **W4A8** 前提下成立（`W909` 的旧口径）；
> `W943` 换成真 kernel 分母得 dot4 30.0% 后改判 −2.05%，`W951` 又按 **W4A4** 重算并进入 `R91`（P0 数值已跑通 0.0648）。
> ②§80-82「W924 的三段配比对 0.2.10 仍成立、R84 上限不必重算」——`W943` 已用真 kernel 重算。
""",

"W942_R61_VALUBUSY_67.md": """
> **【AUDIT24 P1 · 2026-11-04】67.1% 复现了，但口径与留存要补**：本轮同形状复测
> （`kq_bench 16 1024 3 12 1280 2560`，Q4_K）= **64.78 / 68.15 / 68.18 / 68.17，均值 67.3%**，
> CSV 留在 `data/w952pmc/` ⇒ **67.1% 成立**。但 ①本件的原始 csv **已被后续 Q5_1 run 覆盖**
> （`data/w941pmc2` 现存的是 type 7）；②**67.1% 是 M=1024 的形状**，生产形状（每专家 ≈320 行）在 `W945` 测到
> Q4_K **60.6%** —— 两个数都要标形状，不能互相替代；③§4 仍引 dp4a 53.3%（模块口径），见 `W924` 横幅。
""",

"W943_R63_R84_ISA_CENSUS.md": """
> **【AUDIT24 P1 · 2026-11-04】类别百分比加不拢**：§31 写「地址 ≈19.7%」，但同段列出的地址类指令
> 326+132+61+60+33+16 = **628 / 3,411 = 18.4%**；19.7% 是上一轮**模块口径**的遗留数。
> `W945 §7` 与 `R86` 的路径断言引用了 19.7%，应改用 **18.4%**。
> 另：本件据 ISA 静态计数把 R63/R84 判 DONE_NEG，按纪律⑱ 已由 `W947` 重开（R63=OPEN、R84=INFLIGHT）。
""",

"W944_REASSESS_GFX906_PROJECTS.md": """
> **【AUDIT24 P1 · 2026-11-04】§1 的三个数都错（结论不受影响）**：
> ①「88.6%」是**按 offset 列加权**（权重=层号），而且分母是"down 的字节"，不是"专家字节"；
> ②按 `blob_bytes` × 512 专家重算：Q5_1 占**专家总字节 35%**（27.05 / 77.0 GB），在 down 内部占 **86%**，
> 层数 43/48 = **89.6%**；Q8_0 down 是 5 层（11.2% → **9.5%** 的层字节）、Q5_K 1 层（0.2% → **2.7%**）；
> ③「60.5 GB blob」应为 **77.0 GB**（`native_experts.txt` 头部 77,017,907,200 B）。
> ⇒ "Q5_1 是最重的格式"要改成「**Q5_1 是 down 的唯一主格式、占专家字节 35%**」；
> 端到端预期（down 占 prefill 13.8%）与 `R86` 的排序**不变**。
""",

"W945_MX_Q51_REPACK_SOURCE.md": """
> **【AUDIT24 P1 · 2026-11-04】§6.1 的 PMC 必须标形状**：**0.36% / 0.11%** 是
> **16 专家 × 320 token**（生产形状）测的；同一支 `kq_bench` 在 **16 × 1024** 上复测，Q4_K 的
> `MemUnitStalled` = **9.1–9.6%**（`AUDIT24`，CSV 留 `data/w952pmc/`）——大 M 时访存停滞升 **27 倍**。
> ⇒「MMQ 完全不是访存受限」**只在生产形状成立**，引用必须带形状。
> 结论（repack 收益不能按 +84% 外推、必须单内核 A/B）不变。
""",

"W946_GFX906_PROJECTS_LANDSCAPE.md": """
> **【AUDIT24 P1 · 2026-11-04】两处更正**：
> ①§6「prefill 796 → 1251（8K）/ 1561（32K）」**混了两个基线**。README 原文：**796 是"一 slot 的起点"**，
> 而 1251/1561/1977 的对照列是**同一服务配置的上一个默认分支 887/867/877** ⇒ 正确写法
> **887→1251、867→1561、877→1978**，796 只能单独当"起点"讲（+57% 是错的，实际 +41%/+80%/+126%）。
> ②§56-63「我们 0.4.1 vs 社区 v0.7.0、差 3 个 minor」的判据已在 `W948` 自查中作废（版本号不是可比锚点），
> 见 `R90`。
""",

"W948_REPORT_LINT_AND_LLAMA_VERSION.md": """
> **【AUDIT24 P1 · 2026-11-04】版本序的判据无效**：`get_J_max` 在**上游 master 也是 0**
> （本地 `mmq_upstream.cuh` 79,586 B，`grep -c get_J_max` = 0；只有我们 pin 的 `mmq.cuh` 有 1 处）
> ⇒ 它是**我们自己的补丁**，不能当"谁更新"的标志；`3cf03257` 也只出现在 `bench/results/*/README.md`
> （别人机器的记录），不是"我们的 pin"。
> ⇒「三家 fork 都比我们旧」**没有被源码建立**。`R90` 的方向仍可由（与 master 差 587 行 vs 与三家 fork 差 210–223 行）
> 支持，但**必须先建立 pin → 上游 tag 的映射**（已写进 `R90-S1`），再谈"换基线"。
""",
}

changed = []
for name, banner in BANNERS.items():
    p = D + name
    if not os.path.exists(p):
        changed.append((name, "MISSING"))
        continue
    s = io.open(p, encoding="utf-8").read()
    if MARK in s:
        changed.append((name, "already"))
        continue
    lines = s.split("\n")
    # insert right after the H1 title line
    idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), 0)
    lines.insert(idx + 1, banner.rstrip())
    io.open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
    changed.append((name, "banner+"))

# --- numeric corrections inside bodies ---
def sub(name, old, new, count=1):
    p = D + name
    s = io.open(p, encoding="utf-8").read()
    if old not in s:
        changed.append((name, "ANCHOR-MISS"))
        return
    s = s.replace(old, new, count)
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    changed.append((name, "body-fix"))

sub("W922_R68_STOP_BOUND.md",
    "⇒ 而且我们的 99.72% 已经**高于**上游\"打了补丁后\"的 99.74% 同一量级、远高于其\"没打补丁\"的 98.36%。",
    "⇒ 而且我们的 99.72% 与上游\"打了补丁后\"的 99.74% **基本持平（−0.02pp，同一量级）**，远高于其\"没打补丁\"的 98.36%。")

print("\n".join("%-42s %s" % c for c in changed))
