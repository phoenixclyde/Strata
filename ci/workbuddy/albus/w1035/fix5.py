#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1035 §14：分支保护 + Stop 钩子升级到"跑真门"；落账 P412。"""
import io
import shutil

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"
REP = "albus/w1035/reply.md"
MEM = ".workbuddy/memory/2026-11-07.md"

SEC = """
**14. 两条缺口的处置（机主问「怎么办」）。**
① **分支保护：已设**。`PUT /repos/phoenixclyde/Strata/branches/gfx906/mi50/protection` → **200**，读回确认
`contexts=['Static gate (no GPU)']`、`strict=false`、`enforce_admins=false`、`allow_force_pushes=false`、`allow_deletions=false`。
**边界要说清**：GitHub 的「required status checks」只在**合并 PR 前**生效，**直推仍被允许**——因为没开 `restrictions`（限制谁能推）也没开「必须先开 PR」。要彻底堵住直推，就得把主线改成 PR-only，那会改掉现在「本地改完直接推」的工作流，**这条要你定**。
② **Stop 钩子从"看文本"升级为"跑真门"**（v3）。旧版只查消息里有没有四段——贴一段报告就能骗过。现在标记里记着这一回合**最后改的是哪个文件**：改 `albus/` 或 `deploy/` ⇒ 跑 `report_lint` + `report_depth` + `round_ledger` 三个快门，任一 FAIL 就 block 并把门输出当理由；改 `tools/` 等 ⇒ 放行并清标记（改脚本不该补四件套）。三档实测：`tools/` → `{}`；`albus/` 且门全过 → `{}` 且标记清除；**报告缺失 → `{"decision":"block",…}`**（临时移走 `reply.md` 验的，已还原）。
③ **顺带修的 v3 bug**：标记里的路径未小写，与 `ROOT`（已小写）比较恒假 ⇒ 严格分支永远进不去、钩子等于空转。已在 `stop_guard.py` 里 `.lower()`；这就是"写完要测"的又一个例子。
"""

ROW = "\t".join([
    "B8工程", "P412",
    "CI 两条缺口处置：gfx906/mi50 加分支保护；Stop 钩子升级为跑真门（v3）",
    "W1035", "count", "1", "1", "DONE",
    "**W1035 立（机主问「怎么办」）**：① `PUT /branches/gfx906/mi50/protection` → **200**，读回 "
    "`contexts=['Static gate (no GPU)']` / `strict=false` / `enforce_admins=false` / `allow_force_pushes=false` / "
    "`allow_deletions=false` ⇒ **合并 PR 前必须有绿**；但 **required status checks 不管直推**，主线仍可直推（没开 "
    "`restrictions`、没要求先开 PR）——要堵直推必须改 PR-only 工作流，属策略决定。"
    "② `tools/stop_guard.py` v3：标记记「本回合最后改的文件」，改 `albus/`|`deploy/` ⇒ 跑 `report_lint`+`report_depth`+"
    "`round_ledger` 三快门，FAIL 即 block；改 `tools/` ⇒ 放行并清标记。三档实测通过（含「报告缺失 → block」）。"
    "③ 修掉 v3 的路径大小写 bug（未 `.lower()` ⇒ 严格分支永远进不去）。",
    "P411",
])


def main():
    prog = io.open(PROG, encoding="utf-8").read()
    if "\tP412\t" not in prog:
        shutil.copyfile(PROG, PROG + ".bak_w1035g")
        io.open(PROG, "w", encoding="utf-8", newline="\n").write(prog.rstrip("\n") + "\n" + ROW + "\n")
        print("PROGRESS.tsv +P412")

    plan = io.open(PLAN, encoding="utf-8").read()
    o, n = "**352 条 / 已结 270 / 76.7%**", "**353 条 / 已结 271 / 76.8%**"
    if o in plan:
        shutil.copyfile(PLAN, PLAN + ".bak_w1035g")
        io.open(PLAN, "w", encoding="utf-8", newline="\n").write(plan.replace(o, n))
        print("§0.1 -> 353/271/76.8%")

    rep = io.open(REP, encoding="utf-8").read()
    if "14. 两条缺口的处置" not in rep:
        io.open(REP, "w", encoding="utf-8", newline="\n").write(rep.rstrip("\n") + "\n" + SEC)
        print("reply.md +§14")
    rep = io.open(REP, encoding="utf-8").read()
    rep = rep.replace("**352 条 / 已结 270 / 76.7%**（本轮 +4 条：`P407`、`P408`、`P410`、`P411`）",
                      "**353 条 / 已结 271 / 76.8%**（本轮 +5 条：`P407`、`P408`、`P410`、`P411`、`P412`）")
    io.open(REP, "w", encoding="utf-8", newline="\n").write(rep)

    mem = io.open(MEM, encoding="utf-8").read()
    if "分支保护" not in mem:
        with io.open(MEM, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n- **两条缺口处置**：① `gfx906/mi50` 加分支保护（PUT 200：required check=『Static gate (no GPU)』、"
                    "禁 force push / 禁删除、`enforce_admins=false`）——但 **required checks 不管直推**，要堵直推需改 PR-only，待机主定；"
                    "② `stop_guard.py` v3 从「看文本」改「跑真门」：改 `albus/`|`deploy/` 就跑 report_lint+report_depth+round_ledger，"
                    "FAIL 即 block；改 `tools/` 放行并清标记。三档实测通过（含报告缺失→block）。顺带修了路径大小写 bug。账本 `P412`，分母 353/271/76.8%。\n")
        print("memory appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
