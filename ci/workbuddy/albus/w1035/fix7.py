#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 §16：每条阀门的触发器实测 + 证据门接进 deploy.sh（3.5/8）。"""
import io
import shutil

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
REP = "albus/w1035/reply.md"
MEM = ".workbuddy/memory/2026-11-07.md"

SEC = """
**16. 「确保会触发」——逐条实测触发器，不靠承诺。** 机主问「你确保以上会触发执行」。下表每行都是**实测**，不是设计意图：

| 阀门 | 触发条件 | 实测证据 |
|---|---|---|
| `PreToolUse` 钩子 | 本回合 `Write/Edit` 到工作区内 | `.workbuddy/.round_dirty` 在 03:31 那次 Write 后**立刻出现**（63 B） |
| `Stop` 钩子 v3 | 回合结束 且 有标记 | `.hook_seen.log` 有真实调用（`msg_len=2838`、`stop_hook_active=True`、`transcript_path` 齐全）；v3 三档实测：`tools/`→放行、`albus/`→跑三门、**报告缺失→`{"decision":"block"}`** |
| **pre-push 钩子** | `git push` | 两次 push 的输出里都有 `VERIFY/PHASES/BUNDLE/SELF_TEST` + `ROUND_GATE: PASS` |
| GitHub `push` 触发 | 白名单分支 **且** 命中 paths | push `ci/probe-w1035` → **#49 success**；push 主线 `4cd39646` → **#51 success**；`e181bda5` → **#52 success** |
| GitHub `pull_request` 触发 | PR → main | 开 PR #1 → **3 个 run**（#50/#12/#9） |
| 不触发三例 | 非白名单分支 / 非命中路径 / tag | `probe/no-ci` runs=0；同分支换根目录文件无新 run；tag push 全局计数不变 |
| 分支保护 | 合并前必须绿 | **实测到它的边界**：直推时 GitHub 回 `Bypassed rule violations … Required status check "Static gate (no GPU)" is expected` ⇒ **required check 只管合并，不管直推** |
| `deploy.sh` 0/8 `gh_gate` | 装机前必须有**该 sha** 的绿 run | 干跑走到 1/7 之前通过（HEAD 有 #52 绿） |
| **`deploy.sh` 3.5/8 `deploy_gate`（本轮新接）** | 装机前必须有 A/B + 数值证据 | 干跑实测：`D1 PASS`（md5/大小）、`D2 PASS`（166 上 40 个制品）、`D3 REFUSE`、`D4 REFUSE` ⇒ **`DEPLOY STOPPED: deploy gate REFUSE for strata-next`** |

**过程中又抓到一次静默失败**：第一次往 `deploy.sh` 插 3.5 段时用了未加引号的 heredoc，`$BIN/$EXENAME` 先被 shell 展开成空串，`replace` 找不到锚点却照样打印「inserted」——`git show --stat` 显示那次提交**只加了 `deploy_gate.py`，`deploy.sh` 一个字没动**。改成带引号 heredoc + `assert anchor in s` + 插完 `grep` 验证，才是真的插进去了。**教训**：写文件的脚本必须自带"验后置条件"，打印成功不等于成功。

**接线后的状态**：`ci/deploy.sh` 的第 3.5 步现在会对任何缺 A/B / 数值证据的装机 `fail`。也就是说**从这一刻起，没有证据就装不进去**——包括我自己。
"""

ROW = "\t".join([
    "B8工程", "P414",
    "「确保会触发」逐条实测；deploy_gate 接进 deploy.sh 3.5/8（无证据即停）",
    "W1035", "count", "1", "1", "DONE",
    "**W1035 立**：九个阀门逐条实测——`PreToolUse` 造标记（03:31 实测）；`Stop` v3 三档（含报告缺失→block）；"
    "pre-push `ROUND_GATE PASS`（两次 push）；push 触发 #49/#51/#52；PR→3 run；非白名单分支/非命中路径/tag 均不触发；"
    "**分支保护边界实测**：直推时 GitHub 回 `Bypassed rule violations … Required status check is expected` ⇒ required check 只管合并；"
    "`deploy.sh 0/8 gh_gate`（该 sha 的绿 run）+ **新增 `3.5/8 deploy_gate`** 干跑实测 `D1/D2 PASS、D3/D4 REFUSE ⇒ DEPLOY STOPPED`。"
    "**静默失败一例**：未加引号 heredoc 使 `$BIN/$EXENAME` 先展开为空，`replace` 无锚点仍打印 inserted，"
    "`git show --stat` 证实那次只提交了 `deploy_gate.py`；改带引号 + `assert anchor in s` + grep 验证后真正插入。",
    "P413",
])


def main():
    prog = io.open(PROG, encoding="utf-8").read()
    if "\tP414\t" not in prog:
        shutil.copyfile(PROG, PROG + ".bak_w1035i")
        io.open(PROG, "w", encoding="utf-8", newline="\n").write(prog.rstrip("\n") + "\n" + ROW + "\n")
        print("PROGRESS.tsv +P414")

    plan = io.open(PLAN, encoding="utf-8").read()
    o, n = "**354 条 / 已结 272 / 76.8%**", "**355 条 / 已结 273 / 76.9%**"
    if o in plan:
        shutil.copyfile(PLAN, PLAN + ".bak_w1035i")
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan.replace(o, n))
        print("§0.1 -> 355/273/76.9%")

    rep = io.open(REP, encoding="utf-8").read()
    if "16. 「确保会触发」" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply.md +§16")
    rep = io.open(REP, encoding="utf-8").read()
    rep = rep.replace("**354 条 / 已结 272 / 76.8%**（本轮 +6 条：`P407`、`P408`、`P410`、`P411`、`P412`、`P413`）",
                      "**355 条 / 已结 273 / 76.9%**（本轮 +7 条：`P407`、`P408`、`P410`、`P411`、`P412`、`P413`、`P414`）")
    io.open(REP, "w", encoding="utf-8", newline="\n").write(rep)

    mem = io.open(MEM, encoding="utf-8").read()
    if "P414" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n- **「确保会触发」逐条实测（`P414`）**：PreToolUse 造标记（03:31 实测）/ Stop v3 三档含 block / pre-push ROUND_GATE PASS / "
                    "push 触发 #49#51#52 / PR 触发 3 run / 非白名单分支·非命中路径·tag 均不触发；"
                    "**分支保护边界**：直推时 GitHub 明说 `Bypassed rule violations … Required status check is expected` ⇒ 只管合并。"
                    "**deploy_gate 已接进 `ci/deploy.sh` 3.5/8**，干跑实测 `D1/D2 PASS`、`D3/D4 REFUSE`、`DEPLOY STOPPED`。"
                    "**静默失败**：未加引号 heredoc 让 `$BIN` 先展开为空，`replace` 无锚点仍打印 inserted，`git show --stat` 才看出 deploy.sh 没动。账本 `P414`，分母 355/273/76.9%。\n")
        print("memory appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
