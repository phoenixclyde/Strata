#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""remaining steps of the #31188 retraction (first half already applied)."""
import io

ROOT = "D:/workbuddy_space/strata_ws/"


def sub(path, old, new, label):
    p = ROOT + path
    s = io.open(p, encoding="utf-8").read()
    assert s.count(old) == 1, "%s: expected 1, got %d" % (label, s.count(old))
    io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
    print("ok", label)


def main():
    sub("deploy/PROGRESS.tsv",
        "②`AUDIT26` 已核 #31188 的 +17.2% 在 PR 内无性能栏，只能写『作者称』。",
        "②`AUDIT26` 曾判 #31188「PR 内无性能栏」，**AUDIT28 已撤回该误判**：PR 正文有性能表"
        "（DGX Spark +17.2% / 5090 +5.7%），数字属实；不适用是因为 CUDA/MoE 融合路径 + 需改 pack 行交错，"
        "不是因为数字不可核实。",
        "R102")

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
        "plan appendix A")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "这与本项目 `#22174 +17%`、`#31188` 性能栏、`v_mfma` 三次同型：",
        "这与本项目 `#22174 +17%`、`#31188` 性能栏误判（AUDIT28 已撤回）、`v_mfma` 三次同型：",
        "plan 1973")

    sub("deploy/W832_OPT_PLAN_V2.md",
        "即那一轮的赢法是**用 tiling 取代 stream-k**，不是加 stream-k；约 17% 是另一处 2×4090 的报道。",
        "即那一轮的赢法是**禁用 P2P+MoE 场景下的 stream-k**，不是加 stream-k；`AUDIT28` 复核 #22298 正文："
        "它是用 `fastdiv` 降 stream-k 开销，并**仅当 tiling 效率损失 ≤10% 时**才用 tiling 跳过 fixup，"
        "不是无条件「取代」；约 17% 属另一处 2×4090 报道（本轮未核到一手出处，标未复核）。",
        "plan #22298")

    sub("tools/plan_retired.py",
        '("DGX Spark +17.2%", "W1006: #31188 contains no benchmark"),',
        '("DGX Spark +17.2%", "AUDIT28: PR #31188 DOES have a benchmark (2911.4->3410.8); '
        'retired because CUDA/MoE-fusion path is N/A on gfx906, NOT because the number is unverifiable"),',
        "plan_retired reason")

    sub("albus/w1032/reply.md",
        "**7. 未结与边界。**",
        "> **【AUDIT28 更正 2026-11-07】** 相邻的 `AUDIT26` 有一条外网复核结论是错的："
        "它写「#31188 PR 内无性能栏、17.2% 无法核实」，而 PR 正文确有对照表（DGX Spark 2911.4→3410.8 = +17.2%）。"
        "该误判已连带改掉方案 3 处、账本 4 行、`plan_retired.py` 的理由与 `AUDIT26` 源头横幅，"
        "详见 `deploy/AUDIT28_OUTPUT_REMEDIATION.md`。\n\n"
        "**7. 未结与边界。**",
        "W1032 banner")


if __name__ == "__main__":
    main()
