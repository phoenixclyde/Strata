#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 §15：决定 PR-only=否；把「能否落生产」改成判据输出（deploy_gate.py）。"""
import io
import shutil

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
REP = "albus/w1035/reply.md"
MEM = ".workbuddy/memory/2026-11-07.md"

SEC = """
**15. 「由人决定」是错的：能不能落生产应当是判据的输出。** 机主指出图上「绿灯后由人决定」这一节点——他说得对，那是把主观当流程。
**决定：主线不改 PR-only**，依据三条事实：① 单人维护、没有第二个人 review，PR 只会多一道没人看的审批；② 托管 runner **不能编译、没有 GPU**，PR 阶段能验的与本地 pre-push 是同一批静态检查，**不增加任何证据**；③ 真正的决定证据（A/B、数值门）只能在 166 上产生 ⇒ 门设在 merge 时是**设错位置**，应当设在"装进生产之前"。
**因此新增 `tools/deploy_gate.py`**：六条机械判据——`D1 身份`（exe md5/大小，`--live` 时与 166 对齐）、`D2 回滚件`（166 上必须有另一版可回滚）、`D3 性能`（每点 n≥3，Δ 与该次 run **自己的 2×CV** 比）、`D4 数值`（bit-identical 或 KL≤0.0139 且 top-1≥99%）、`D5 配置面`（config md5 = register 生成值）、`D6 证据链`（report + 账本行 + 当日记忆 + §6.5 回写块）。**任何一条拿不出证据就 REFUSE**——「没有证据」本身即拒绝理由。
**实测（当场对在产引擎跑）**：`D1 PASS`（`5e63174d…` / 42,947,088 B）、`D2 PASS`（166 上 40 个引擎制品）、`D6 PASS`，而 **`D3 REFUSE`（没有 A/B 证据）、`D4 REFUSE`（没有数值门结论）⇒ 整条 REFUSE**。这正说明它不是盖章器：连现在生产的 001 都过不了它，因为当初装它时并没有走这套证据。
图上那个节点从此改成：**⑤ GitHub 静态门 → ⑥ 166 编译 → `deploy_gate.py` PASS/REFUSE → 装或不装**。人只提供目标与阈值（一次性政策），逐次判定交给门。
"""

ROW = "\t".join([
    "B8工程", "P413",
    "「能否落生产」改为判据输出：新增 deploy_gate.py（六条 D1–D6）；主线不改 PR-only",
    "W1035", "count", "1", "1", "DONE",
    "**W1035 立（机主：「人决定是主观的」）**：① **决定不改 PR-only**——单人维护无 reviewer、托管 runner 无 GPU/无编译、"
    "真证据只能在 166 产生 ⇒ 门该设在装机前而非 merge 时；② 新增 `tools/deploy_gate.py`：D1 身份（exe md5，`--live` 对齐 166）/ "
    "D2 回滚件（166 上有另一版）/ D3 性能（每点 n≥3，Δ 与**当次 run 自己的 2×CV** 比）/ D4 数值（bit-identical 或 "
    "KL≤0.0139 且 top-1≥99%）/ D5 配置面（config md5 = register 生成值）/ D6 证据链（report + 账本行 + 记忆 + §6.5 块）；"
    "**缺证据即 REFUSE**；③ 实测对在产 001：D1/D2/D6 PASS、**D3/D4 REFUSE ⇒ 整体 REFUSE**（证明它不盖章）。",
    "P412",
])


def main():
    prog = io.open(PROG, encoding="utf-8").read()
    if "\tP413\t" not in prog:
        shutil.copyfile(PROG, PROG + ".bak_w1035h")
        io.open(PROG, "w", encoding="utf-8", newline="\n").write(prog.rstrip("\n") + "\n" + ROW + "\n")
        print("PROGRESS.tsv +P413")

    plan = io.open(PLAN, encoding="utf-8").read()
    o, n = "**353 条 / 已结 271 / 76.8%**", "**354 条 / 已结 272 / 76.8%**"
    if o in plan:
        shutil.copyfile(PLAN, PLAN + ".bak_w1035h")
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan.replace(o, n))
        print("§0.1 -> 354/272/76.8%")

    rep = io.open(REP, encoding="utf-8").read()
    if "15. 「由人决定」是错的" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply.md +§15")
    rep = io.open(REP, encoding="utf-8").read()
    rep = rep.replace("**353 条 / 已结 271 / 76.8%**（本轮 +5 条：`P407`、`P408`、`P410`、`P411`、`P412`）",
                      "**354 条 / 已结 272 / 76.8%**（本轮 +6 条：`P407`、`P408`、`P410`、`P411`、`P412`、`P413`）")
    io.open(REP, "w", encoding="utf-8", newline="\n").write(rep)

    mem = io.open(MEM, encoding="utf-8").read()
    if "deploy_gate" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n- **决定：主线不改 PR-only**（单人无 reviewer / runner 无 GPU 无编译 / 真证据只能在 166 产生 ⇒ 门设在装机前）。"
                    "新增 `tools/deploy_gate.py`：D1 身份·D2 回滚件·D3 性能(2×CV)·D4 数值(KL/top-1 或逐位)·D5 配置面·D6 证据链，"
                    "缺证据即 REFUSE。实测对在产 001：D1/D2/D6 PASS，**D3/D4 REFUSE ⇒ 整体 REFUSE**（不盖章）。账本 `P413`，分母 354/272/76.8%。\n")
        print("memory appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
