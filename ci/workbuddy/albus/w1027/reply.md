**一、生产容器（10 字段）**

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` / `strata-gfx906:0.2.11-101`（image `2e7539eeb76b`） |
| 2 | 运行中引擎 | `strata-0.1.57-001`（**崩溃后回滚**），md5 `5e63174dbd7cc04e5fa1b5fc455b2a73`，42,947,088 B |
| 3 | config | md5 `53ac61e0c663a6a46b7a5aa2e610bf43`（回滚后逐字节复原）；exe=`/data/bin/strata-0.1.57-001`；args **37**；env **9** |
| 3a | args 明细（37 项 / 19 个 flag） | `--pack /data/packs/ud-q4_k_xl` `--native /models/…/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` |
| 3b | env 明细（9 项） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_ROCBLAS_TUNING=…` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` `STRATA_PREFILL_TIMING=1` |
| 4 | 健康 | `/health` ok、`loaded:true`、restarts=0、StartedAt `2026-11-06T11:59:46Z` |
| 5 | 资源隔离 | 容器内 `ulimit -l` = unlimited（`--ulimit memlock=-1:-1`）；host **16,473,712 KB**；引擎 `VmLck` = 0 kB |
| 6 | 显存布局 | expert cache `7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | **本轮动用了** `ci/rollback.sh --exe strata-0.1.57-001 --apply`（ledger 记 `ROLLBACK`）；试版 `strata-0.1.57-003` md5 `a8e86e76…` 留在 `/data/bin` |
| 8 | 本轮改动 | 引擎 2 次（003 部署 → 001 回滚）；镜像/容器未改；disk = build = running = `5e63174d…` 三方一致 |
| **9** | **ROCm 版本** | `.info/version` = **10.1.0**；HIP 运行时 **7.16.26323-0000000**（`hipconfig`）；clang **24.0.0git**；`ROCM_BUILD=7.14.0-gfx906+20260802001858` |
| **10** | **llama.cpp 版本** | **b11062** = `3cf03257f219afbe7334045ff7c6a06ac68c627d`（2026-09-20）；树 hash `6feee58927d5f1efd38e72bbc1db061d` |

**二、主线** gfx906/mi50 @ 360cbd4c · tag `mi50-0.2.11-r33-9` · 落后上游 0 / 领先 72 / merges 0 · 脏 0 行；实验分支 `exp/lcpp-b12169` = `7fdd5d3c`。
**三、本次落生产** 引擎 2 次（003 → 001）；**重启 2 次**；停机合计约 **2.5 分钟**（watchdog 60 s + 两次启动）；回滚件动用 1 次；代码面 0 提交进主线。
**四、进度** 297 条 / 已结 213 / **71.7%**；队列 **R99（S1 已崩，待定）→** R95 → R94 → R91 → R89 → R46 → R49 → R50。

---

## 五、你问「走 ci/cd 流程吗」——不走，而且 CI 现在是关的

| 问题 | 事实 |
|---|---|
| 有 CI 定义 | 有，10 个 workflow；`downstream-gate.yml` 在改 `src/`、`include/`、`ci/` 时跑静态门 |
| 它现在跑吗 | **不跑**。手动 dispatch 返回 **422 `Actions has been disabled for this repository`**；最后一次 run 是 **#44 @ `372106ed`**，之后 5 次提交全无 run |
| 那 #42–#44 为什么红 | 卡在 step 6「Round gate」；我用 `git clone --depth 1` 复现 **PASS** ⇒ 不是代码问题，原因未定位 |
| 构建/部署在 CI 里吗 | **从来不在**。workflow 头部逐字：*"This is deliberately not a build: compiling the engine needs ROCm and 8-10 minutes of a self-hosted machine."* |

所以现状是「**本地门 + 手工部署**」：`round_gate --ci`、`round_close`、pre-push hook 都在本机跑。我此前写「CI」时指的是这些本地门 —— 这点必须改口，**本地绿 ≠ 远端绿**，这是 W1018 已经付过一次学费的形状。

要恢复远端眼睛只有两条路：①在 GitHub UI 启用这个 fork 的 Actions（一分钟，需要你点）；②在 166 上挂自托管 runner（能编能测，但生产机当 runner 有风险）。

## 六、R99 的 S1：编过了，但 cap 在 75-token 的 prefill 上

`exp/lcpp-b12169` = `7fdd5d3c`：`Context` 加 spec 缓冲（`include/strata/prefill/moe_mmq.hpp:87`）、`build_tile_spec` kernel、`mmq_args` 第 5 字段换 `tile_spec`（构造点 `src/prefill/moe_mmq.cu:505`）、`nchannels_y` 从 n 改成 **1**、第 24 字段 `ntj = ceil(total/J) + n`。全量 **154/154、0 error**，二进制 `strata-0.1.57-003`（44,776,344 B，md5 `a8e86e76…`）。

- **门1（数值）**：968-token 英文的 48-token 贪心输出 **逐字节一致**（224 字符）；短英文前缀一致；但 1565-token 中文的 content/reasoning 分配不同 ⇒ **不算干净通过**。
- **门2（速度）**：`cfg_apply` 在 **75-token 短 prompt** 上 **HTTP 503**。日志：`reading the prompt: 75 tokens` 连续 **60 s** 无进展 → watchdog 判 hang → `exit code -6`（SIGABRT）。
- **处置**：`ci/rollback.sh` 47 s 恢复，config md5 回 `53ac61e0…`，ledger 记 `ROLLBACK`。

三个候选原因（**都未验证，不写成结论**）：①`p.bounds` 末项 ≠ `p.total_rows` 时 spec 索引越界写、破坏 mmq scratch（`include/strata/prefill/moe_mmq.hpp:96` 是缓冲所在）；②`ntj` 与 grid 的 z 维假设不一致（`nchannels_y` 从 n 改 1 之后要重核 `nti/ntkw`）；③短 prompt 下 `n_slots` 只有 2（J=64、75 列），空 tile 与尾部槽位的覆盖关系与上游不同 —— `bounds` 来自 `src/prefill/prefill.cpp:5318` 的 `rel`，它的末项是否等于 `total_rows` 正是要先核的。

## 七、这次崩，是「我的实现错」还是「上游不行」

必须分清，否则会把 bug 记成"上游慢"：`#31047` **只改分派**（哪些 tile 归哪个专家），不改算术 —— 所以它**不应该**改变任何数值，更不该 hang。现在既出现中文分叉又 hang，**最可能是我的 spec 生成错**，不是上游的问题。这也是 S1 存在的意义：把"适配错"关在一个可回滚的 2 分钟窗口里，而不是到 S3 才发现。

## 八、下一步（R99 仍 OPEN，但不进 S2）

1. 先在 **host 侧**把 `bounds` 抓一份（D2H 一次），核对单调性、末项是否等于 `total_rows`、`n_slots` 与实际上限；
2. 用这份 bounds 复算 spec，与"上游 helper 在小规模 ids 上的输出"逐条对比（离线、无 GPU 风险）；
3. 只有 spec 逐条一致，才重新编译上机；
4. 若两轮之内修不好，R99 记 **DONE_NEG**（理由：分派层重写成本 > 潜在收益，且 b12129 已实测 −4%）。

## 九、门与同步

`plan_lint` A–F PASS；`pointer_lint` / `plan_retired` / `audit_index` / `bundle.py` / `release_check`（10/10）全 PASS；
`REPORT_LINT: PASS (14 fields)`；`REPORT_DEPTH: PASS`；`ROUND_CLOSE: PASS`。六件权威件双侧逐字节。
本轮新增：§6.5 回写·W1027、`P362`（Actions 被禁用）、`P363`（S1 崩溃与回滚）。
