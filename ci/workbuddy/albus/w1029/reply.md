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
| 8 | 本轮改动 | 生产零改动、零重启；仓库 1 提交 `bc56628a`（4 文件）；token 落到 `~/.config/strata/gh_token`(600)；disk = build = running = `5e63174d…` 三方一致 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ bc56628a · tag `mi50-0.2.11-r33-11` · 落后上游 0 / 领先 74 / merges 0 · `origin == HEAD` · 脏 0 行；实验分支 `exp/lcpp-b12169` = `7fdd5d3c`。
**三、本次落生产** 引擎 0 次；镜像 0 次；**重启 0 次**；停机 0 分钟；回滚件未动用；代码面 1 提交（`bc56628a`，4 文件）。
**四、进度** 303 条 / 已结 219 / **72.3%**；队列 **R99**（S1 待修）→ R95（`P335`）→ R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、邮箱里没有「禁用」通知，只有 7 封「Run failed」

收件箱 + 垃圾箱全查了：GitHub 来的全是 `Run failed: Downstream gate`（`f013f9b`/`759a4ed`/`e21b1b0`/`1ec9c75`/`e887862`/`56fd43a`/`372106e`），**没有任何**关于 Actions 被禁用或欠费的通知。所以不是「GitHub 发了通知我没看」，是它压根没发。

## 六、`#42–#44` 连红 9–11 秒，真因是一行日志里的一行

`GET /actions/jobs/<id>/logs` 要绕开带 `Authorization` 的 302 重定向才拿得到正文，拿到后尾部逐字：

```
ROUND_GATE: FAIL (1)
  - selftest_pin.py: [BAD] baseline: both declarations agree   rc=2
```

`rc=2` 是 **python 打不开文件**，不是 pin 判错。根因在 `ci/selftest_pin.py:13`：

```python
RC = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"   # 我的工作仓，runner 上没有
```

runner 上没这个路径 ⇒ 每个用例都以 `rc=2` 结束 ⇒ 唯一必须通过的一例（baseline）必然 `[BAD]`。
**一个路径 bug 穿着 pin bug 的外衣，把每一次推送都判红。** 修法是把它改成 `__file__` 相对（`ci/selftest_pin.py:13`），
文件缺失时在 `ci/selftest_pin.py:59` 直接 `SystemExit`，不再被计成 `[BAD]`。

判据不是"我觉得好了"：**depth-1 clone**（没有工作仓路径、没有 tag，正是 runner 的样子）跑 `ci/round_gate.py --ci` →
`ROUND_GATE: PASS`、`SELFTEST: 4/4`。这条修完后，下一次能跑起来的 run 就是绿的。

## 七、门交回 GitHub：部署必须有一条绿色的 GitHub run

新增 `ci/gh_gate.py`（`ci/gh_gate.py:96` 是查 run 那段）：给定 sha，要求 `downstream-gate` 有一条
`completed = success` 的 run；`exit 6` = 没 run 或还在跑，`7` = 失败并打 URL，`8` = API/无 token。
`ci/deploy.sh:41` 的第 0 步换成它，W1028 的本地回执降级成一句提示。

工作流也补了一条：`actions/checkout` 加 `fetch-depth: 0` + `fetch-tags: true`（`.github/workflows/downstream-gate.yml:50`）——
depth-1 检出**没有 tag**，凡是读 tag 的检查都会因「与本次改动无关」的原因变红，这是 CI 里最常见的假红。

三段式现在是：**GitHub run（判据）→ 本地 round_gate（推送前自检）→ 166 接收端回执（第二双眼睛）**，顺序不能反。

## 八、还差你点一下：仓库自己的 Actions 开关是关的

| 探针 | 结果 |
|---|---|
| `GET /repos/phoenixclyde/Strata/actions/permissions` | `{"enabled": true, "allowed_actions": "all"}` |
| `PUT` 同接口 / `PUT /actions/workflows/403412814/enable` | 都是 **204**（看起来成功） |
| `POST …/downstream-gate.yml/dispatches` | **422 `Actions has been disabled for this repository`** |
| 同账号**非 fork** 仓 `phoenixclyde/vllm-gfx906-routeb` 同一调用 | 422 **`Workflow does not have 'workflow_dispatch' trigger`** ⇒ 那边 Actions 正常 |
| 推 `faaeb1c6`、`bc56628a` 后各等 30 s | `actions/runs` 无新 run；`gh_gate.py` 返回 6 |
| workflow state | 一直 `active` |

三条结论：① **不是账号级**（同账号另仓正常）；② **不是 workflow 级**（state 一直 active）；
③ 是**这个仓库自己的开关**，REST API 翻不动，只有 Web UI 能开。

**请你点两处之一**：仓库 → **Settings → Actions → General → Allow all actions**；
或 **Actions 标签页顶部的 `I understand my workflows, go ahead and enable them`**。
点完我这边一条命令就能验：`python3 ci/gh_gate.py --wait 300` 会等到第一条 run，给 `PASS` 或失败 URL。
（若你想让我彻底不依赖这个仓库的开关，还有一条备选：在非 fork 仓建镜像跑 CI——但那是换仓库，不是修开关，等你发话。）

## 九、在此之前部署是被拒的，这是故意的

`deploy.sh` 现在第一步就问 GitHub，没有绿 run 就 `fail`。所以本轮的"落生产"是 0 / 0 / 0 ——
**不是我忘了部署，是门不让**。能被「云端不方便」绕过的门不算门，上一轮（W1028）刚用接收端回执补过一次，
这一轮按你的要求把它交回 GitHub，本地那两段只做自检。

## 十、举一反三：三次「在我这儿是绿的」都是环境泄漏

- W1028：hook 里的 `GIT_DIR` 没剥 → 门在对裸库说话，还把真仓写成 `core.bare=true`；
- W1029：`RC` 写成工作仓绝对路径 → runner 上 `rc=2`，44 次 run 后的每次推送都红；
- 同一类还有 depth-1 无 tag → 读 tag 的检查无关地红。

共同点：**判据依赖了「我这台机器的状态」**——环境变量、绝对路径、git 历史深度。
规矩收紧一句：**凡是会跑在别人机器上的脚本，只准用 `__file__` 相对路径、只准读显式传入的环境**；
写完必须在**干净 clone**里跑一遍，那才是 runner 的样子。

## 十一、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` / `MIRROR_CHECK` 全 PASS；
`GATE_RECEIPT` 对 `bc56628a` PASS（166 接收端已受门）；`gh_gate.py` 对 `bc56628a` 返回 **6**（无 run，Actions 关着）。
六件权威件双侧逐字节。本轮新增：§6.5 回写·W1029、`P367`（CI 红真因）、`P368`（门交回 GitHub）、`P369`（仓库级开关与证据）。
生产未动，现役性能仍是 prefill@2K **530.43 tok/s** / @8K **716.02 tok/s**（W1022 记录，本轮未复测）。
