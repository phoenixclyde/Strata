**一、生产容器（10 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`）——本轮未重建 |
| 2 | 运行中引擎 | `strata-0.1.57-001`，md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-06T11:59:46Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | `strata-0.1.57-001`（现役）、`strata-0.1.57-002/003`（b12129 / S1 试版）、镜像 `0.2.10-101`、旧容器 `strata166-407-old`；`ci/rollback.sh --exe … --apply` |
| 8 | 本轮改动 | 生产零改动、零重启；仓库 1 提交 `faaeb1c6`（4 文件）；新建 gate 裸库；**主仓 `.git/config` 被误写成 `core.bare=true` 已复原**；disk = build = running = `5e63174d…` 三方一致 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ faaeb1c6 · tag `mi50-0.2.11-r33-10` · 落后上游 0 / 领先 73 / merges 0 · `origin == HEAD` · 脏 0 行；实验分支 `exp/lcpp-b12169` = `7fdd5d3c`。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 1 提交（`faaeb1c6`，4 文件 **+121/−0**）+ 新建一个 bare 门库（**78 MiB**，含两份回执 **656 B / 650 B**）。
**四、进度** 300 条 / 已结 216 / **72.0%**；队列 **R99**（S1 待修）→ R95（`P335`）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、「按业内通用来」= 门放在改动躲不开的地方，而不是我的 shell 里

先说 GitHub 这条路为什么必须放弃，而且**它的 API 会说谎**：

| 探针 | 结果 |
|---|---|
| `GET /repos/phoenixclyde/Strata/actions/permissions` | `{"enabled": true, "allowed_actions": "all"}` |
| `PUT` 同一接口重开 | **204**（看起来成功） |
| `POST …/downstream-gate.yml/dispatches` | **422 `Actions has been disabled for this repository`** |
| 换 `terminal-minimal-server.yml` / `upstream-watch.yml` | 同样 422 ⇒ **仓库级**，不是某个 workflow |
| `GET /actions/runs` | 最后一条 **#44 @ `372106ed` @ 2026-11-05T18:15:37Z**，其后 5 个提交零 run |
| 仓库字段 | `fork=true`、`archived=false`、`disabled=false`、`admin=true` |

所以判据改成：**别看 `enabled`，看 `actions/runs` 里有没有你那个 sha**。要重开只能走 GitHub UI 的 fork 提示，或在 166 挂自托管 runner —— 两条都不该是门的前提，否则门又变成「取决于别人家的开关」。

## 六、落地的四件东西（都不依赖 GitHub）

| 位置 | 做什么 |
|---|---|
| `/home/albus/strata166/gate/strata-gate.git`（bare） | `hooks/pre-receive` 把每个推来的提交 `git archive` 解到临时目录，在**那里**跑 `ci/round_gate.py --ci`；红则整推被拒（`pre-receive` 第 34 行走 `env -u GIT_DIR …`） |
| 同 hook 写 `receipts/<sha>.json` | sha / ref / 时间 / runner / python / **7 个门脚本的 md5**；单份 **650 B**，跑完一遍门约 **25 s** |
| `ci/gate_receipt.py`（新） | 缺失 → exit **3**（`gate_receipt.py:66`）；门脚本在回执之后被改 → exit **4**（`gate_receipt.py:83`） |
| `ci/deploy.sh` 第 0 步（新，`deploy.sh:42`） | `gate_receipt.py --sha $(git rev-parse HEAD)` 不过就 `fail`，部署动作本身依赖回执 |

推送顺序进 `deploy/W838_REMOTE_POLICY.md`：`git push gate gfx906/mi50`（受门）→ `git push origin gfx906/mi50`（镜像）。GitHub 仍是记录之地，**但不再是门**。客户端的 `pre-push` 也放行了这个本地裸库（`ci/hooks/pre-push:15`）。

## 七、证明：四条正向 + 四条负向，全带退出码

| 测试 | 结果 |
|---|---|
| `git push gate gfx906/mi50` | `GATE PASS` → `receipts/faaeb1c6….json` |
| **绕过客户端**推坏树：`git push --no-verify gate HEAD:tmp/gate-negative`（`BUNDLE.tsv` 的 `phase_ms` 510→400） | `! [remote rejected] (pre-receive hook declined)`，**分支在裸库里不存在** |
| 回执缺失：`gate_receipt.py --sha 9104cc00` | `FAIL … has no receipt`，**rc=3** |
| 回执过期：回执之后给 `ci/round_gate.py` 追加一行注释 | `FAIL stale -- gate changed after the receipt: ci/round_gate.py`，**rc=4** |
| 复原后 | `PASS faaeb1c6db77 (receipt 2026-11-06T13:14:27Z, runner ubuntu2204lts, 3.12.3)`，rc=0 |
| 部署第 0 步 dry run | `=== 0/8 gate receipt === GATE_RECEIPT: PASS` 后继续 1/7 |

注意第二条：客户端 `pre-commit`/`pre-push` 已经能挡，但只有 `--no-verify` 绕过去、被**接收端**独立拒绝，才算证明门不在我手里。

## 八、第一次推送就抓到两个真缺陷，其中一个动了生产仓库

1. **`receive-pack` 会导出 `GIT_DIR` 与 quarantine 变量，而 `git -C <dir>` 不覆盖它。** hook 里的门于是在对裸库说话而不是临时检出：`git describe --tags` 答 "No names found"，一次本来合格的推送被拒。
2. **更严重、而且早就存在**：`ci/selftest_pin.py` 造临时仓库时用 `git init`，在 hook 里跑时被导出的 `GIT_DIR` 带偏，**把真实工作树 `/home/albus/strata166/pr/strata-fork` 初始化成 bare**（`core.bare=true`）。之后每条 git 命令都报 `this operation must be run in a work tree`；我是靠推 gate 时那句莫名其妙的 fatal 才发现的，已 `git config core.bare false` 复原（HEAD `360cbd4c`、dirty 0 逐项核过）。
   修法：`sh()` 剥掉 `GIT_DIR/GIT_OBJECT_DIRECTORY/…` 七个变量（`ci/selftest_pin.py:20`），`fixture()` 加 `rev-parse --is-inside-work-tree` 断言（`ci/selftest_pin.py:49`），失败当场 `SystemExit`，不再伪装成「pin 红了」。

## 九、举一反三：门的三种死法与第四次同型

这个项目的门已经死过四次，形状完全一样——**门不在变更的必经路径上，或它的证据不可校验**：

- W1018：证据件只在笔记本上（`ci/state` 被 gitignore）→ CI 连红 5 次没人发现；
- W1025：报告门是全文级匹配，「正文提过」就算过 → 表里缺字段照样绿；
- W1027：Actions 早在 #44 之后就没跑过，我却继续报「run #31 success」；
- W1028（本轮）：门终于从「我跑过」变成「接收端跑过、回执在、门脚本没变」。

三条硬规矩写进技能：**门必须在接收端执行**；**回执必须能被工作副本以外的东西验证**；**判「CI 有没有跑」只能看 runs 里有没有该 sha**。`strata-release` 新增 §2a 完整记录这两条命令顺序与两个 `GIT_DIR` 陷阱。

## 十、R99 本轮不推进，理由写清

`exp/lcpp-b12169` = `7fdd5d3c` 保留；S1 的 `tile_spec` 版仍在 75-token prompt 上 hang（`exit -6`），三个候选原因（bounds 末项、`ntj` 与 grid z、空 tile 覆盖）**均未验证**。这轮门正在把「工作副本里的绿」变成「接收端的绿」，此时改内核无法归因，也不该占停机窗口。

生产未动，现役性能仍是 W1022 记录的 prefill@2K **530.43 tok/s** / @8K **716.02 tok/s**（本轮生产零改动、零重启，故未复测；显存布局 `21.79 GiB` / `882 MiB free` 也逐项未变）。

## 十一、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` / `release_check`（10/10）全 PASS；`GATE_RECEIPT: PASS`；六件权威件双侧逐字节（`MIRROR_CHECK: PASS`）。本轮新增：§6.5 回写·W1028、`P364`（接收端门）、`P365`（`selftest_pin` 把真仓写成 bare 的事故）、`P366`（Actions 不可用与判据）。
