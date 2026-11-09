# W1047 · CI/CD 全覆盖回溯 + B3 从候选到装机门

**一、生产容器（10 字段，2026-11-07 22:3x 装机后只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | **`strata-0.1.57-hc4b`** · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B |
| 3 | config | md5 **`9e2df560fdb88f684a3f2fb7b15d9ad5`** · `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env **12** |
| 3a | args 明细 | `--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE(_MAX)` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` 未改；**新增 `STRATA_HC_DOWN_DP4A=1`、`STRATA_HC_DOWN_DP4A_MAX_T=6`（P527/P528）** |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T14:33:49Z` · 冷启动 41 s · KV 错误计数 0 |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | used 33,493,749,760 / total 34,342,961,152 ⇒ **VRAM free 849,211,392 B（0.79 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 (7.62 GiB) |
| 7 | 回滚件 | `/data/bin` **57 件**；`attn`（`3b758f88…`）、`kvg` 在册；config 备份 `tmp/w1047/cfg_preinstall_w1047.bak`；rollback = 恢复 config **并重启容器**（≈45 s） |
| 8 | 本轮改动 | **换引擎 1 次 + 改 config 1 次**：`attn→hc4b`、`3dde8801→9e2df560`；disk = build = running；**重启 7 次 / 停机 1810 s / 装机 1 / 回滚 0** |
| 9 | ROCm | 10.1.0 · HIP 7.16.26323 · clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 2 / 落后 0 / 脏 0 行，上游本轮未重算。CI/工具分支 `ci/w1047-coverage @ 9e780f581`；B3 候选 `gfx906/hc-dp4a @ 03509d1b` 已装机但未合主线。

**三、本次落生产** — **换引擎 1 次 + 改 config 1 次**；D1–D6 全 PASS 后冷启动。**重启 7 次 / 停机 1810 s / 装机 1 / 回滚 0**。

**四、进度** — **482 条 / 已结 389 / 80.7%**。队列：~~P533 已装机~~ → R110/R112（真实 P/V dump）→ R111（GPU CI runner）→ R109 的 A1/A5 → R106 → R107…

## 1. 上轮结论的纠错

- **pre-push 不是「从未存在」**：`pr/k10` 是 linked worktree，`.git/hooks` 不是有效路径；共享 hooks 在 `pr/strata-fork/.git/hooks`。W1046 修 installer，W1047 修 `round_gate --status` 的路径解析。GitHub 外证：worktree 的共享 hooks 应通过 `git rev-parse --git-path hooks`/`--git-common-dir` 解析。
- **「今天 CI 零触发」在 18:51 后过期**：API 已见 `ci/w1046-gates`、`ci/w1046-hooks` success。真正的缺口是生产/候选分支和本地工具不在覆盖面，现已补齐。
- **cold bench timeout 不是产品故障**：我传 `fused_gr_bench 1 4 4 2`，`iters=1` 使中位数向量为空并越界；改 `64 ... 3` 后正常。

## 2. CI/CD 全覆盖回溯

- `ci/w1047-coverage @ 9e780f581`：4446 文件 / 744k 行；`ci/workbuddy/**` 镜像项目自产脚本、补丁、报告和实验代码。
- **全工作区 SHA-256**：`workspace_manifest.tsv` 23197 行；镜像文件另有 `selected_scripts.tsv`；`artifact_ledger.tsv` 覆盖 58 个引擎制品的 recipe/CI/manual/UNTRACKED 状态。
- **workflow**：push 改为全分支，paths 增加 `tools/**`、`deploy/params/**`、`albus/**`、`waves/**`；PR 目标扩到 `gfx906/**`/`ci/**`；新增 `workbuddy_syntax.py` + `workbuddy_selftest.py`。
- **回溯触发**：`workflow_dispatch` 让 7 个生产/候选 sha 全部有 `Downstream gate` success，包括 `af797b90`、`deb41e12`、`e0ce7c96`、`03509d1b`、`9e780f58`。
- **语法清零**：修复 5 个 Python/shell 结构错误 + 7 个 CRLF shell，最终 1741 Python + 1214 shell 全过；自测 14/14。
- **Push Protection 实证**：第一次 push 被 OAuth 形状密钥拦截；已脱敏、更新哈希、从干净基线重建提交，**未使用 bypass**。

## 3. B3：不是凭 bench 装，而是三道门都过

- **性能**：clean bench 发现无门控候选 T7/8 down +45%…+64%；`hc4b` 以 `MAX_T=6` 回退后 T7/8 持平。n=3 T4：down **39.87→30.17 µs（−24.33%）**，read **78.0→68.3 µs**。
- **数值**：同一 `hc4b` off/on 的 4 个全词表 logits：top-1 **100.00%**，KL mean **0.00087** / max **0.00221**。
- **任务**：16K/32K/64K × 0/50/100% needle，off **9/9**、on **9/9**，`cached=0`。
- **配置面**：config 仅 exe 指针 + 两个 env；P527/P528 已登记。`deploy_gate` D1–D5 全 PASS。

落点与门都可复核：Q8_0 HC down 的真实热路径是 `src/kernels/cuda/fused_gr.cu:2337`（fast 变体）与 `src/kernels/cuda/fused_gr.cu:2588`（launch_q8 分派）；q8_1 镜像契约在 `include/strata/kernels/fused_gr.hpp:48`；硬件 dot4 生效层在 `include/strata/platform/hip_compat/strata_hip.h:237`。`MAX_T` 门控只改分派，不碰原内核。

## 4. 仍不冒充完成

- `R111`：GitHub self-hosted runner 数为 **0**，编译/数值/装机仍是 166 手工窗口；GPU CI 需要单独安全设计。
- `R112/R110`：PV-dot8 合成上限 1.483× 但 rel-rms 6.23%；必须做真实 P/V dump，不能外推。
- `R107` 审计欠账继续存在；本轮回溯修复的是工程覆盖面，不等于审计结清。

装机完成：新引擎 md5 `05330748…`、config `9e2df560…`、冷启动 41 s、两个 env 容器内实证。回滚件与备份齐备。
