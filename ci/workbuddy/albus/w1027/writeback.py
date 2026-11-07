import io

PLAN = "deploy/W832_OPT_PLAN_V2.md"
PROG = "deploy/PROGRESS.tsv"

s = io.open(PLAN, encoding="utf-8").read()

BLOCK = '''
### 回写 · W1027（CI 实际被禁用；R99 的 S1 第一次尝试崩在 prefill，已回滚）

**一、CI/CD 的真实状态（机主问「你走 ci/cd 流程吗」）**

| 问题 | 事实 |
|---|---|
| 有 CI 定义吗 | 有，10 个 workflow，其中 `downstream-gate.yml` 在每次改 `src/`、`include/`、`ci/` 时跑静态门（`verify.py` + `round_gate.py --ci`） |
| 它现在跑吗 | **不跑**。`POST /actions/workflows/downstream-gate.yml/dispatches` 返回 **422 `Actions has been disabled for this repository`**；最后一次 run 是 **#44 @ `372106ed`**，之后 4 次提交（`c81ada30`/`e8878625`/`56fd43a0`/`372106ed`/`360cbd4c`）**一次都没触发** |
| 那 #42–#44 为什么红 | 卡在 step 6「Round gate」；用 shallow clone 复现（`git clone --depth 1`）**PASS** ⇒ 不是代码问题，原因未定位（Actions 被关前的环境差异） |
| 构建/部署在 CI 里吗 | **从来不在**。`downstream-gate.yml` 头部逐字："This is deliberately not a build: compiling the engine needs ROCm and 8-10 minutes of a self-hosted machine." 理由写在 `deploy/CI_CD_BLUEPRINT.md` |
| 那靠什么 | 本地对等门：`ci/round_gate.py --ci`、`albus/w1002/round_close.py`、pre-push hook（`ci/hooks`）。**但这只是"我跑过"，不是"远端跑过"** |

一句话：**代码走的是"本地门 + 手工部署"，不是 CI/CD**；而唯一的远端眼睛（fork 的 Actions）现在是关的。

**二、R99 / S1（单提交 #31047 + 自己生成 tile_spec）第一次尝试：崩了**

- 移植：`exp/lcpp-b12169` = `7fdd5d3c`（Context 加 spec 缓冲、`build_tile_spec` kernel、`mmq_args` 第 5 字段换 `tile_spec`、第 15 字段 `nchannels_y=1`、第 24 字段 `ntj = ceil(total/J)+n`）；全量编 **154/154、0 error**，二进制 `strata-0.1.57-003` md5 `a8e86e76…`。
- 门1（数值）：48-token 指纹里 **968-token 英文逐字节一致**（224 字符），短英文前缀一致；但 1565-token 中文的 `content/reasoning` 分配不同（48-token 预算边界）⇒ **不算干净通过**。
- 门2（速度）：`cfg_apply` 在 **75-token 的短 prompt** 上 **HTTP 503**。日志：`reading the prompt: 75 tokens` 连续 60 s 无进展 ⇒ watchdog 判定 hang ⇒ `the engine stopped unexpectedly (exit code -6)`（SIGABRT）。
- 处置：`ci/rollback.sh --exe strata-0.1.57-001 --apply`，47 s 恢复健康，config md5 回 `53ac61e0…`，ledger 记 `ROLLBACK`。停机约 2 分钟（1 次 watchdog + 1 次重启）。
- 三个候选原因（**均未验证，不写成结论**）：①`p.bounds` 的末项不等于 `p.total_rows` 时 spec 索引越界写，破坏 mmq scratch；②`ntj` 与 grid 的 z 维假设不一致（我们把 `nchannels_y` 从 n 改成 1，需核对 `ntkw/nti` 的组合）；③短 prompt 下 `n_slots` 很小（J=64、75 列 ⇒ 2 条 tile），空 tile 与尾部槽位的覆盖关系与上游不同。

**三、纪律**

S1 没有过门1/门2，**不进 S2**，更不碰镜像与 pin。主 tree 仍 `360cbd4c`（dirty 0），生产 `strata-0.1.57-001`。
'''
if "回写 · W1027" not in s:
    s = s.rstrip("\n") + "\n" + BLOCK

s = s.replace("| 进度分母 | **295 条 / 已结 211 / 71.5%** |", "| 进度分母 | **297 条 / 已结 213 / 71.7%** |", 1)
io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)

ROWS = [
 ("B8工程", "P362",
  "GitHub Actions 已被禁用（dispatch 返回 422）：最近 5 次提交没跑过任何 CI，我此前报的「CI」都是本地门",
  "W1027", "DONE_NEG",
  "**W1027 立**：`POST /repos/phoenixclyde/Strata/actions/workflows/downstream-gate.yml/dispatches` → **422 Actions has been disabled for this repository**；"
  "最后一次 run **#44 @ 372106ed**，其后 `c81ada30`/`e8878625`/`56fd43a0`/`360cbd4c` **全无 run**。"
  "shallow clone（`git clone --depth 1`）复现 `round_gate --ci` **PASS** ⇒ #42–#44 的红不是代码问题，原因未定位。"
  "构建/部署按 `downstream-gate.yml` 头部声明**从不在 CI**（需 ROCm + 8–10 min 自托管机）。结论：现状是「本地门 + 手工部署」，不是 CI/CD；恢复远端眼睛需在 GitHub UI 启用 fork 的 Actions。",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1027"),
 ("B8工程", "P363",
  "R99/S1 第一次尝试：tile_spec 版全量编过，但 75-token prefill 触发 watchdog hang（exit -6），已回滚",
  "W1027", "DONE_NEG",
  "**W1027 立**：`exp/lcpp-b12169`=`7fdd5d3c`（`build_tile_spec` kernel + `mmq_args` 换 `tile_spec` + `nchannels_y=1` + `ntj=ceil(total/J)+n`），154/154 编过，`strata-0.1.57-003` md5 `a8e86e76…`。"
  "门1：968-token 英文 48-token 指纹**逐字节一致**，但中文 case 的 content/reasoning 分配不同 ⇒ 不算干净通过。"
  "门2：`cfg_apply` 在 **75-token prompt** 上 503；日志 `reading the prompt: 75 tokens` 持续 60 s 无进展 ⇒ watchdog `exit code -6`。"
  "已 `rollback.sh` 回 001（47 s 健康，config md5 回 `53ac61e0…`）。候选原因（未验证）：bounds 末项≠total_rows 导致 spec 越界写 / ntj 与 grid z 维假设不一致 / 短 prompt 下空 tile 覆盖关系。**不进 S2。**",
  "deploy/W832_OPT_PLAN_V2.md §6.5 回写·W1027"),
]
lines = io.open(PROG, encoding="utf-8").read().split("\n")
hi = next(i for i, l in enumerate(lines) if not l.startswith("#") and l.count("\t") >= 9)
ID = lines[hi].split("\t").index("id")
have = {l.split("\t")[ID] for l in lines if l.count("\t") >= 9}
add = ["\t".join([b, pid, item, src, "count", "1", "1", st, note, ref])
       for b, pid, item, src, st, note, ref in ROWS if pid not in have]
if add:
    while lines and lines[-1] == "":
        lines.pop()
    lines += add + [""]
io.open(PROG, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("W1027 block + %d rows" % len(add))
