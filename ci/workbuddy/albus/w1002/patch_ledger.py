# -*- coding: utf-8 -*-
"""W1002 ledger: engineering delivery, not a tuning arm."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()

rows = [
    ["B5本机缺口", "P282", "交付门：round_gate/verify/hooks/workflow 接上调用者", "W1002", "count", "1", "1", "DONE",
     "**W1002（2026-11-05 21:5x）**：机主三问「完整移植了吗 / 四项报告呢 / CI-CD 呢」+ 追问「对应的门呢 / 还有个 lint」。查实：pre-commit 只有 gate.py --source-only，report_lint 在本机无人调，W999/W1001 的 bench 源码在 /tmp 与 build-tab 没进仓库，16 提交未推。整改：ci/repack_ab/（README+RESULTS.tsv+PORT_STATUS.md+两份 .cu+run.sh+verify.py）、ci/report_lint.py、ci/round_gate.py 入仓；pre-commit/pre-push/downstream-gate.yml 三处调用 round_gate --ci；本机 albus/w1002/round_close.py 串四个 lint。**负向自测 5/5**：伪造 ratio / 清空 PORT_STATUS / 删 fair-AB 标记 / 去掉 workflow 调用 / 让 report_lint 恒真，门均 FAIL 且恢复后 PASS。",
     "ci/README.md"],
    ["B5本机缺口", "P283", "plan_lint 判据 E 整改 + 方案归一回写 W832 §6.5", "W1002", "count", "1", "1", "DONE",
     "**W1002**：tools/plan_lint.py 实跑 rc=1，报 4 份未登记 PLAN（W940/W951/W954/W986）。根因是 W986–W1001 一直往 W986_PLAN_V3.md 追加 V3.1–V3.9，违反 W832 §0.0「方案只许一份」。整改（不绕过 lint）：V3.9 队列与判据回写 W832 §6.5 为唯一执行序；W986 头部标 SUPERSEDED/不构成队列；四份按真实角色登记进 PLAN_FROZEN。复跑 plan_lint **PASS**（未登记 0 份、未结项全在方案里、R 号全有账）。",
     "deploy/W832_OPT_PLAN_V2.md §6.5"],
    ["B5本机缺口", "P284", "积压 17 提交推送，CI 端到端实跑", "W1002", "count", "1", "1", "DONE",
     "**W1002**：git 原本 ahead 16（origin tip 5f73cd15），GitHub 静态门一次都没见过这几轮。连同本轮提交共 17 个 push 到 gfx906/mi50（5f73cd15..ab68576c），pre-commit/pre-push 实跑通过；GitHub API 查得 **Downstream gate run #25 completed/success @ ab68576c**；166 上 strata-ci check **18 checks / 0 failed**、gate.py --source-only 11 checks / 0 failed、round_gate --status PASS（remote HEAD == local HEAD）。生产配置与二进制零改动。",
     "CI_CD_RUNBOOK.md §10"],
]

io.open(P, "w", encoding="utf-8", newline="").write("\n".join(lines + ["\t".join(r) for r in rows]) + "\n")
print("PROGRESS +3 rows (P282/P283/P284)")
