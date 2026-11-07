#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AUDIT28 P0: retract AUDIT26's false external-fact claim about PR #31188.

Web evidence (GitHub API, 2026-11-07): PR #31188 body DOES contain a Performance
table; created 2026-10-26, merged/closed 2026-10-28, updated_at == closed_at
(so it was not edited after AUDIT26's 2026-11-05 check).
  DGX Spark (GB10) Qwen3-30B-A3B Q4_K_M 2911.4 -> 3410.8 t/s (+17.2%)
  RTX 5090        Qwen3-30B-A3B Q4_K_M 12611.7 -> 13330.3 t/s (+5.7%)
The right conclusion is "real number, wrong hardware/path for gfx906", not
"no benchmark / cannot be verified / author's claim only".
"""
import io

ROOT = "D:/workbuddy_space/strata_ws/"


def sub(path, old, new, label):
    p = ROOT + path
    s = io.open(p, encoding="utf-8").read()
    assert s.count(old) == 1, "%s: expected 1, got %d" % (label, s.count(old))
    io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    print("ok", label)


CORRECT = ("**【AUDIT28 撤回 2026-11-07 · P0】** 原写「PR 内无性能栏 / 17.2% 无法核实 / 只能写作者称」，"
           "经 GitHub API 逐字复核为**错**：PR #31188 正文有 `### Performance` 表（`llama-bench -p 16384 "
           "-b 2048 -ub 2048 -r 5`）：DGX Spark Qwen3-30B-A3B Q4_K_M **2911.4→3410.8 t/s = +17.2%**、"
           "RTX 5090 **12611.7→13330.3 = +5.7%**，`created_at=2026-10-26`、`updated_at=closed_at=2026-10-28`"
           "（不是事后补的）。⇒ 正确结论是「**数字属实，但 CUDA + MoE 融合路径，gfx906 不适用**」"
           "（与 #29948 同族，`P391`/`R102` 已判否），而不是「数字不可核实」。")


def main():
    # 1. the audit artefact itself
    sub("deploy/AUDIT26_W898_W1005.md",
        "| 方案 §6.5 W1003 块 | 「#31188 MoE DGX Spark +17.2% / 5090 +5.7%」 | **PR 内没有性能栏**；两处独立报道都写「无法核实 17.2%，不能归因于该 PR」。引用只能写「作者称」 |",
        "| 方案 §6.5 W1003 块 | 「#31188 MoE DGX Spark +17.2% / 5090 +5.7%」 | " + CORRECT + " |",
        "AUDIT26 table row")

    sub("deploy/AUDIT26_W898_W1005.md",
        "## 2 结论：0 个 P0，3 个 P1，2 个 P2\n",
        "## 2 结论：0 个 P0，3 个 P1，2 个 P2\n\n"
        "> **【AUDIT28 更正】** 下表最后一行（#31188）的「外网复核」结论已被本件撤回："
        "它把一条**可核实的上游实测数字**误判为「无性能栏」，并连带把方案、账本与 `plan_retired.py` 的理由写错。"
        "#22174 那条（关掉 stream-k、双 3090 +9.67%）复核成立，保留。\n",
        "AUDIT26 §2 banner")

    # 2. index row
    sub("deploy/AUDIT_INDEX.md",
        "（#22174 方向/数字、#31188 无性能栏）",
        "（#22174 方向/数字成立；**#31188「无性能栏」是误判，AUDIT28 已撤回**）",
        "index AUDIT26 row")

    # 3. ledger notes -- append corrections, keep the original wording as history
    sub("deploy/PROGRESS.tsv",
        "②#31188 PR 无 benchmark，两处独立报道均称 17.2% 无法核实。结论不变（都不对症），理由已改。",
        "②#31188 PR 无 benchmark，两处独立报道均称 17.2% 无法核实。结论不变（都不对症），理由已改。"
        "  **【AUDIT28 撤回 P0】第②条是错的**：PR #31188 正文确有 `### Performance` 表"
        "（DGX Spark 2911.4→3410.8 = +17.2%、5090 12611.7→13330.3 = +5.7%），`updated_at==closed_at==2026-10-28`。"
        "正确理由 = 数字属实但 CUDA/MoE 融合路径、gfx906 不适用；「都不对症」的结论不变，**理由换掉**。",
        "P302")

    sub("deploy/PROGRESS.tsv",
        "宣称「prefill 最高 +17.2%」但**原文明确说没有对照数据、不能归因**；CUDA-only，我们是 HIP/gfx906。",
        "宣称「prefill 最高 +17.2%」但**原文明确说没有对照数据、不能归因**；CUDA-only，我们是 HIP/gfx906。"
        "  **【AUDIT28 更正】**「原文无对照数据」是误读：PR 正文有对照表（master 2911.4 / PR 3410.8），"
        "且 perplexity 逐位相同；应改成「有对照、但只在 CUDA + MoE 融合路径上，HIP/gfx906 不适用」。",
        "R96")

    sub("deploy/PROGRESS.tsv",
        "PR #31188（MoE 版）宣称 +17.2% 但**原文明确无对照数据、不能归因**。",
        "PR #31188（MoE 版）宣称 +17.2% 但**原文明确无对照数据、不能归因**。"
        "  **【AUDIT28 更正】** 该句已撤回：PR #31188 有 `master vs PR` 对照表（见 P302），"
        "误读只影响理由，不影响「融合类收益强依赖硬件/形状」这个结论。",
        "P280")

    sub("deploy/PROGRESS.tsv",
        "②`AUDIT26` 已核 #31188 的 +17.2% 在 PR 内无性能栏，只能写「作者称」。",
        "②`AUDIT26` 曾判 #31188「PR 内无性能栏」，**AUDIT28 已撤回该误判**：PR 正文有性能表"
        "（DGX Spark +17.2% / 5090 +5.7%），数字属实；不适用是因为 CUDA/MoE 融合路径 + 需改 pack 行交错，"
        "不是因为数字不可核实。",
        "R102")

    # 4. plan
    sub("deploy/W832_OPT_PLAN_V2.md",
        "（#29948 稠密 +7.1%；#31188 MoE，**PR 内无性能栏**，`W1006` 外网复核两处独立报道均写「无法核实 17.2%」——引用它时只能说「作者称」）",
        "（#29948 稠密 +7.1%；#31188 MoE，**【AUDIT28 更正】PR 正文确有性能表**：DGX Spark +17.2% / RTX 5090 +5.7%，"
        "数字属实；不适用是因为 CUDA + MoE 融合路径、gfx906 且需改 pack 行交错，不是「无法核实 / 作者称」）",
        "plan 1140")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "| 「#31188 DGX Spark **+17.2%**」 | R96 的立项理由 | `W1006` | **PR 内无性能栏**，两处独立报道称无法核实 ⇒ 只能写「作者称」 |",
        "| 「#31188 DGX Spark **+17.2%**」 | R96 的立项理由 | `W1006` → **AUDIT28 更正** | "
        "原写「PR 内无性能栏 / 只能写作者称」**已撤回**：PR 有 `master 2911.4 → PR 3410.8` 对照表；"
        "退役原因改为「CUDA/MoE 融合路径，gfx906 不适用」，不是数字不可核实 |",
        "plan 附录A row")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "这与本项目 `#22174 +17%`、`#31188` 性能栏、`v_mfma` 三次同型：",
        "这与本项目 `#22174 +17%`、`#31188` 性能栏误判（AUDIT28 已撤回）、`v_mfma` 三次同型：",
        "plan 1973")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "即那一轮的赢法是**用 tiling 取代 stream-k**，不是加 stream-k；约 17% 是另一处 2×4090 的报道。",
        "即那一轮的赢法是**禁用 P2P+MoE 场景下的 stream-k**，不是加 stream-k；`AUDIT28` 复核 #22298 正文："
        "它是用 `fastdiv` 降 stream-k 开销，并**仅当 tiling 效率损失 ≤10% 时**才用 tiling 跳过 fixup，"
        "不是无条件「取代」；约 17% 属另一处 2×4090 报道（本轮未核到一手出处，标未复核）。",
        "plan 1213 #22298")

    # 5. the gate that forbade a real number with a false reason
    sub("tools/plan_retired.py",
        '("DGX Spark +17.2%", "W1006: #31188 contains no benchmark"),',
        '("DGX Spark +17.2%", "AUDIT28: PR #31188 DOES have a benchmark (2911.4->3410.8); '
        'retired because CUDA/MoE-fusion path is N/A on gfx906, NOT because the number is unverifiable"),',
        "plan_retired reason")

    # 6. previous round report: source banner
    sub("albus/w1032/reply.md",
        "**7. 未结与边界。**",
        "> **【AUDIT28 更正 2026-11-07】** 本件 §5 未提、但相邻的 `AUDIT26` 有一条外网复核结论是错的："
        "它写「#31188 PR 内无性能栏、17.2% 无法核实」，而 PR 正文确有对照表（DGX Spark 2911.4→3410.8 = +17.2%）。"
        "该误判已连带改掉方案 3 处、账本 4 行、`plan_retired.py` 的理由与 `AUDIT26` 源头横幅，详见 `deploy/AUDIT28_OUTPUT_REMEDIATION.md`。\n\n"
        "**7. 未结与边界。**",
        "W1032 banner")


if __name__ == "__main__":
    main()
