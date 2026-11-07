# -*- coding: utf-8 -*-
"""[W863] Record the CI/CD build-out in the repo ledger (commit list + how the automation works)."""
import subprocess

REPO = "/home/albus/strata166/pr/strata-fork"
P = REPO + "/docs/DOWNSTREAM.md"
src = open(P, encoding="utf-8").read()

ROW6 = "| 6 | `ci: narrow the two push-triggered workflows`"
anchor_end = src.find("\n", src.find(ROW6))
if anchor_end < 0:
    raise SystemExit("ABORT: row 6 not found")

NEW = """
| 7 | `ci: add the downstream gate and the upstream watcher` | 新增 3 个文件（**不改上游任何文件**）：`ci/gate.py`（配置面检查）、`downstream-gate.yml`（每次改 `src/`/`include/`/`CMakeLists.txt` 就跑）、`upstream-watch.yml`（每日查上游差距，开/更新一个 issue） | `strata-ci check` 在 166 上 18 项全过；GitHub run 45cee350 **success** |
| 8 | `ci(watch): check out gfx906/mi50 explicitly` | `schedule`/`workflow_dispatch` 只跑**默认分支上存在**的 workflow，所以 `main` 上放了一份副本；副本必须显式 checkout 主线，否则它比较的是 `main`（永远 0 落后） | 手动 dispatch run 41291722718 **success**，日志 `BEHIND: 0` |"""

src = src[:anchor_end] + NEW + src[anchor_end:]

# refresh the distance line
import re
ahead = subprocess.run(["git", "-C", REPO, "rev-list", "--count", "upstream/main..HEAD"],
                       capture_output=True, text=True).stdout.strip()
behind = subprocess.run(["git", "-C", REPO, "rev-list", "--count", "HEAD..upstream/main"],
                        capture_output=True, text=True).stdout.strip()
src = re.sub(r"\| 与上游距离 \| 落后 \*\*\d+\*\* / 领先 \d+",
             "| 与上游距离 | 落后 **%s** / 领先 %s" % (behind or "0", ahead or "?"), src)

CI_ADD = """
### 自动化在哪里（2026-11-01 建好）

| 位置 | 做什么 | 入口 |
|---|---|---|
| GitHub（no GPU） | 配置面静态门：R 表形状/取值、`getenv` 真存在、`-DNDEBUG`、hip_compat 路径、备份文件、台账锚点 | `ci/gate.py --source-only`，workflow `Downstream gate` |
| GitHub（no GPU） | 每日 09:23 CST 比较 `gfx906/mi50` 与 `upstream/main`，有差距就开（或更新）一个 `upstream-watch` issue，追平后自动关闭 | workflow `Upstream watch`（`main` 上有副本，因为 schedule 只认默认分支） |
| 166 | 同一份门 + 构建树 + 生产 config，共 18 项 | `/home/albus/strata166/ci/strata-ci check` |
| 166 | 单 TU 编译 → 部署 → 重启 → 健康门 → 台账 | `strata-ci build` / `deploy --apply` / `rollback --last` |

**上游监视故意不自动 rebase**，三条理由都是硬约束：
① 用 `GITHUB_TOKEN` 推的 commit **不会触发任何 workflow**，CI 不会跑，分支会"看着绿其实没测"；
② 我们的 rebase 改写历史，推主线必须 force-push，无人值守做这件事就是在赌主线；
③ rebase 之后必须重编 + 逐位等价，而云端 runner 没有 GPU。
所以自动化只到"发现 + 提醒"，rebase 留给 `strata-ci watch && git rebase upstream/main`。

> 部署门用工具强制，不靠记性：`strata-ci deploy` 在 `HEAD` 没有 `mi50-*` tag 时直接拒绝（已实测）。
"""

if "### 自动化在哪里（2026-11-01 建好）" not in src:
    src = src.replace("\n## 跟随上游（四步）", CI_ADD + "\n## 跟随上游（四步）", 1)
    print("ledger: automation section added")

open(P, "w", encoding="utf-8").write(src)
print("rows 7-8 added; distance -> behind %s / ahead %s" % (behind, ahead))
