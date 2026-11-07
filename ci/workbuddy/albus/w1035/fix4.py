#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 §13：CI 实测（不是读记录）+ 更正 W1027 的过时结论 + 账本 P411。"""
import io
import re
import shutil

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
REP = "albus/w1035/reply.md"
MEM = ".workbuddy/memory/2026-11-07.md"

CORR = ("> **2026-11-07 03:34 复核（W1035，实测非记录）**：本节第一条已过时——**Actions 没有禁用**。"
        "`POST /actions/workflows/downstream-gate.yml/dispatches` 返回 **204**，新 run **#48 completed/success**"
        "（job「Static gate (no GPU)」三步全绿）；最近一次历史 run **#47 success 2026-11-06T13:50Z**。"
        "另：`ci/round_gate.py` 只存在于仓库工作树（166，7327 B / 11-06 21:14），**本机工作区 `ci/` 里没有**，"
        "所以“本地对等门”在本机跑不了，本机只有 `albus/w1002/round_close.py`。\n\n")

SEC = (
    "\n**13. CI/CD 实测（不是读记录）：它是活的，而且我刚把它跑绿了。** "
    "`GET /repos/phoenixclyde/Strata` → 200（`archived=false`、`disabled=false`、default_branch=`gfx906/mi50`）；"
    "`GET /actions/workflows` → 10 个，`Downstream gate` **state=active**（另 5 个 `disabled_manually` 是当年有意关的 PR 治理类）；"
    "`GET /actions/runs` → 累计 **71** 次，最近 **#47 success 2026-11-06T13:50Z**；"
    "`POST .../downstream-gate.yml/dispatches`（ref=`gfx906/mi50`）→ **204**，**#48 由 in_progress 转 completed/success**，"
    "job「Static gate (no GPU)」的 `Syntax of the 166 tooling` / `Config-face checks` / `Round gate (evidence, report lint, …)` 三步全 success。"
    "⇒ **`W1027` 里「Actions has been disabled、dispatch 返 422」是过时结论**，已在那个块首加复核横幅（保留原文，不重写历史）。"
    "**顺带查出一个真缺口**：`ci/round_gate.py` 只存在于 166 仓库（7327 B / 11-06 21:14），**本机工作区的 `ci/` 只有 `bundle_budget` 与 `prefill_phases`** ——"
    "我上一轮引用的「本地对等门」在本机根本跑不了，本机只有 `round_close.py`。"
    "\n**钩子会不会真触发（机主：「我都不信」）**：`.workbuddy/.hook_seen.log` 有真实调用记录，payload 字段齐全"
    "（`last_assistant_message` msg_len=2838、`stop_hook_active=True`、`transcript_path`、`session_id`、`hook_event_name`）；"
    "更早那次 block 也是它打出来的（乱码那条）。所以「触发」这一条是实measured，不是声明；仍未验的是**桌面版是否真的按 block 让 agent 继续**——"
    "从 `stop_hook_active=True` 这一字段的存在看，它是按 \"block 过一次再放行\" 的协议在走。\n"
)


def main():
    plan = io.open(PLAN, encoding="utf-8").read()
    if "2026-11-07 03:34 复核（W1035" not in plan:
        shutil.copyfile(PLAN, PLAN + ".bak_w1035f")
        i = plan.find("### 回写 · W1027")
        j = plan.find("\n", i) + 1
        plan = plan[:j] + "\n" + CORR + plan[j:]
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan)
        print("W1027 block: correction banner added")

    prog = io.open(PROG, encoding="utf-8").read()
    if "\tP411\t" not in prog:
        row = "\t".join([
            "B8工程", "P411",
            "CI/CD 实测：远端 Actions 未禁用（dispatch 204、#48 success）；本机缺 ci/round_gate.py",
            "W1035", "count", "1", "1", "DONE",
            "**W1035 立（机主令「你给我测 ci/cd，你习惯性看记录」）**：`GET repo` 200（archived=false / disabled=false / "
            "default_branch=`gfx906/mi50`）；`GET actions/workflows` 10 个，`Downstream gate` **active**（5 个 "
            "`disabled_manually` 是当年有意关的 PR 治理类）；`runs` 累计 71，最近 **#47 success 2026-11-06T13:50Z**；"
            "`POST downstream-gate.yml/dispatches`（ref=gfx906/mi50）**204**，**#48 completed/success**"
            "（Static gate (no GPU)：166 tooling 语法 / Config-face checks / Round gate 三步全绿）。"
            "⇒ `W1027` 的「Actions has been disabled、422」**已过时**，已在该块首加复核横幅（保留原文）。"
            "**真缺口**：`ci/round_gate.py` 只在 166 仓库（7327 B / 11-06 21:14），本机 `ci/` 只有 bundle_budget 与 "
            "prefill_phases ⇒「本地对等门」在本机跑不了，本机只有 `round_close.py`。",
            "P410",
        ])
        shutil.copyfile(PROG, PROG + ".bak_w1035f")
        io.open(PROG, "w", encoding="utf-8", newline="\n").write(prog.rstrip("\n") + "\n" + row + "\n")
        print("PROGRESS.tsv +P411")

    plan = io.open(PLAN, encoding="utf-8").read()
    o, n = "**351 条 / 已结 269 / 76.6%**", "**352 条 / 已结 270 / 76.7%**"
    if o in plan:
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan.replace(o, n))
        print("§0.1 -> 352/270/76.7%")

    rep = io.open(REP, encoding="utf-8").read()
    if "13. CI/CD 实测" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply.md +§13")
    rep = io.open(REP, encoding="utf-8").read()
    rep = rep.replace("**351 条 / 已结 269 / 76.6%**（本轮 +3 条：`P407`、`P408`、`P410`）",
                      "**352 条 / 已结 270 / 76.7%**（本轮 +4 条：`P407`、`P408`、`P410`、`P411`）")
    io.open(REP, "w", encoding="utf-8", newline="\n").write(rep)

    mem = io.open(MEM, encoding="utf-8").read()
    if "CI 实测" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n- **CI 实测（03:34，机主令「测，不要看记录」）**：Actions **没禁用**——dispatch 返 **204**、"
                    "run **#48 success**（Static gate：166 tooling / Config-face / Round gate 三步绿），最近历史 #47 success；"
                    "`W1027` 的 422 结论已过时，已加复核横幅。**本机缺 `ci/round_gate.py`**（只在 166 仓库），"
                    "所以本机能跑的只有 `round_close.py`。账本 `P411`，分母 352/270/76.7%。\n")
        print("memory appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
