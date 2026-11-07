# -*- coding: utf-8 -*-
import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

# 1) progress denominator: +3 rows (P364/P365/P366)
a = "| 进度分母 | **297 条 / 已结 213 / 71.7%** |"
b = "| 进度分母 | **300 条 / 已结 216 / 72.0%** |"
assert a in s, "denominator anchor"
s = s.replace(a, b, 1)

# 2) mainline row
a2 = "`mi50-0.2.11-r33-8` @ `372106ed`"
b2 = "`mi50-0.2.11-r33-10` @ `faaeb1c6`"
assert a2 in s, "tag anchor"
s = s.replace(a2, b2, 1)
a3 = "behind 0 / ahead 71 / merges 0）"
b3 = "behind 0 / ahead 73 / merges 0）"
assert a3 in s, "ahead anchor"
s = s.replace(a3, b3, 1)

BLOCK = """

---

## §6.5 回写 · W1028（2026-11-06 21:00–21:25）CI 按业内做法落到"接收端"

### 一、GitHub Actions 这条路走到头了，而且它的 API 会说谎

| 探针 | 结果 |
|---|---|
| `GET /repos/phoenixclyde/Strata/actions/permissions` | `{"enabled": true, "allowed_actions": "all"}` |
| `PUT` 同一接口重开 | **204**（看似成功） |
| `POST …/workflows/downstream-gate.yml/dispatches` | **422 `Actions has been disabled for this repository`** |
| 换 `terminal-minimal-server.yml` / `upstream-watch.yml` 再试 | 同样 422 ⇒ **仓库级**，不是某个 workflow |
| `GET /actions/runs` | 最后一条 **#44 @ `372106ed` @ 2026-11-05T18:15:37Z**，之后 5 个提交零 run |
| 仓库字段 | `fork=true`、`archived=false`、`disabled=false`、`admin=true` |

**判据**：`actions/permissions.enabled` **不能**用来判断 CI 是否在跑；要看 `actions/runs` 里有没有你那个 sha。
要重开只能走 GitHub UI 的 fork 提示，或在 166 挂自托管 runner —— **两条路都不该是门的前提**，
否则门又变成"取决于别人家的开关"。

### 二、按业内做法：门放在改动躲不开的地方

| 位置 | 内容 | 谁也无法绕过 |
|---|---|---|
| `/home/albus/strata166/gate/strata-gate.git`（bare） | `hooks/pre-receive` 把每个推来的提交解包到临时目录，在里面跑 `ci/round_gate.py --ci`；红则整推被拒 | 接收端，`--no-verify` 只跳过客户端钩子 |
| 同一 hook 的 `receipts/<sha>.json` | 绿跑记录：sha / ref / 时间 / runner / python / **每个门脚本的 md5** | 工作副本里造不出来 |
| `ci/gate_receipt.py`（新） | 部署前校验回执：缺失 → exit 3；**门脚本在回执之后被改过 → exit 4** | 把"I 事后改门"和"I 稍后再跑"都堵住 |
| `ci/deploy.sh` 第 0 步（新） | `gate_receipt.py --sha $(git rev-parse HEAD)` 不过就 `fail` | 部署动作本身依赖回执 |

推送顺序写进 `deploy/W838_REMOTE_POLICY.md`：`git push gate gfx906/mi50` → `git push origin gfx906/mi50`。
GitHub 仍是"记录之地"，但**不再是门**。

### 三、两次推送抓到两个真缺陷（都是"在我这儿是绿的"家族）

1. **`receive-pack` 会导出 `GIT_DIR` 与 quarantine 变量，而 `git -C <dir>` 不覆盖它。**
   于是 hook 里的门在对**裸库**说话而不是临时检出：`git describe --tags` 答 "No names found"，
   于是一次本来合格的推送被拒。修法：读树用显式 `--git-dir`，跑门用 `env -u GIT_DIR -u GIT_OBJECT_DIRECTORY …`。
2. **更严重，而且早就存在**：`ci/selftest_pin.py` 造临时仓库时用 `git init`，在 hook 里跑时被导出的
   `GIT_DIR` 带偏，**把真实工作树 `/home/albus/strata166/pr/strata-fork` 初始化成了 bare**
   （`core.bare = true`），之后每条 git 命令都报 `this operation must be run in a work tree`。
   已 `git config core.bare false` 复原，并在 `sh()` 里剥掉 `GIT_*`、`fixture()` 里断言临时目录
   确实是 work tree（`rev-parse --is-inside-work-tree`），把这类失败变成"当场报错"而不是"pin 红了"。

### 四、证明（每条都有退出码，不是叙述）

| 测试 | 命令 | 结果 |
|---|---|---|
| 正常推 | `git push gate gfx906/mi50` | `GATE PASS` → `receipts/faaeb1c6….json` |
| 服务端拒绝（绕过客户端） | `git push --no-verify gate HEAD:tmp/gate-negative`（BUNDLE.tsv 的 `phase_ms` 510→400） | `! [remote rejected] (pre-receive hook declined)`，**分支未建立** |
| 回执缺失 | `gate_receipt.py --sha 9104cc00` | `FAIL … has no receipt`，**rc=3** |
| 回执过期 | 回执后给 `ci/round_gate.py` 追加一行注释 | `FAIL stale -- gate changed after the receipt: ci/round_gate.py`，**rc=4** |
| 复原 | 同上还原 | `PASS faaeb1c6db77 (receipt 2026-11-06T13:14:27Z, runner ubuntu2204lts, 3.12.3)`，rc=0 |
| 部署第 0 步 | `ci/deploy.sh --src …/build-r28 --exe strata-0.1.57-001`（dry run） | `=== 0/8 gate receipt === GATE_RECEIPT: PASS` 后继续走 1/7 |

### 五、R99 停在哪里（本轮未推进）

`exp/lcpp-b12169` = `7fdd5d3c` 仍保留；S1 的 tile_spec 版在 75-token prompt 上 hang（`exit -6`），
三个候选原因（bounds 末项、`ntj` 与 grid z、空 tile 覆盖）**均未验证**。本轮不碰它，理由：
门的问题正在把"工作副本里的绿"变成"接收端的绿"，此时改内核无法归因。

### 六、纪律

门只认三件东西：**接收端跑过**、**回执在**、**门脚本没变**。本地 `round_gate` 从"唯一证据"降为"推送前的自检"。
"""

s = s.rstrip("\n") + BLOCK
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
print("plan updated")

rows = [
    ("B8工程", "P364",
     "门移到接收端：166 上的 bare gate 库 + pre-receive 跑 round_gate、写回执、deploy 第 0 步校验",
     "W1028", "DONE",
     "**W1028 立**：fork 的 Actions 对所有 dispatch 回 422（而 `/actions/permissions` 报 `enabled:true`、`PUT` 回 204）⇒ 不再把门建在 GitHub 上。"
     "`/home/albus/strata166/gate/strata-gate.git` 的 `pre-receive` 把推送解包到临时目录跑 `ci/round_gate.py --ci`，绿则写 `receipts/<sha>.json`（含 7 个门脚本 md5）。"
     "`ci/gate_receipt.py` 判缺失(rc=3)/门被改过(rc=4)；`ci/deploy.sh` 第 0 步调用它。"
     "证明：正推 PASS；`--no-verify` 推坏 BUNDLE 被 `pre-receive hook declined` 且分支未建立；缺失 rc=3；过期 rc=4。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1028"),
    ("B8工程", "P365",
     "`ci/selftest_pin.py` 在 git hook 里把真实工作树初始化成 `core.bare=true`（事故）；已修 + 断言",
     "W1028", "DONE",
     "**W1028 立**：`receive-pack` 导出 `GIT_DIR`，而 `git -C <dir>` 不覆盖它 ⇒ 自测造临时仓库的 `git init` 打到真实仓库上，"
     "把 `/home/albus/strata166/pr/strata-fork` 写成 `core.bare = true`，之后所有 git 命令报 `this operation must be run in a work tree`（发现于第一次受门推送）。"
     "已 `git config core.bare false` 复原（HEAD `360cbd4c`、dirty 0 核对过）。修法：`sh()` 剥 `GIT_DIR/GIT_OBJECT_DIRECTORY/…` 七个变量；"
     "`fixture()` 增加 `rev-parse --is-inside-work-tree` 断言，失败即 `SystemExit`，不再伪装成 \"pin 红\"。",
     "ci/selftest_pin.py"),
    ("B8工程", "P366",
     "GitHub Actions 不可用的事实与判据：`enabled:true` + dispatch 422 + 最后 run #44；判 CI 要看 `actions/runs` 有无该 sha",
     "W1028", "DONE_NEG",
     "**W1028 立**：`GET /actions/permissions` → `{enabled:true, allowed_actions:all}`；`PUT` 重开回 **204**；dispatch 仍 **422**；"
     "`terminal-minimal-server.yml`/`upstream-watch.yml` 同样 422 ⇒ 仓库级。最后 run **#44 @ `372106ed` @ 2026-11-05T18:15:37Z**，其后 5 提交零 run。"
     "仓库 `fork=true / archived=false / disabled=false / admin=true`。结论：**API 的 enabled 不能用来判断 CI 是否在跑**，"
     "要重开只能 UI 或自托管 runner，而门已不依赖它（P364）。",
     "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1028"),
]

lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
head = lines[hi].split("\t")
ID = head.index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in rows if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("progress +%d" % len(add))
