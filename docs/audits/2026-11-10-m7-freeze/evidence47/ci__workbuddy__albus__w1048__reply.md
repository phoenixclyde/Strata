# W1048 四件套 — 复核五条全量入方案 + 历史变更 CI/CD 全量回溯

**一、生产容器（10 字段，2026-11-07 23:3x 只读）**

| # | 字段 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `2d765942e041` · `strata-gfx906:0.2.11-101` · restarts=0 |
| 2 | 运行中引擎 | `strata-0.1.57-hc4b` · md5 `0533074826258d5f96c4b65bc0ad33df` · 43,679,864 B，未换件 |
| 3 | config | md5 `9e2df560fdb88f684a3f2fb7b15d9ad5` · `exe=/data/bin/strata-0.1.57-hc4b` · args 38 / env 12，未改 |
| 3a | args 明细 | 38 项逐字未动：`--serve` `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` `--pool-workers 10` `--kv-grow` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE(_MAX)` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` `STRATA_PREFILL_TIMING` `STRATA_GFX906_ATTN_DP4A=1` `STRATA_HC_DOWN_DP4A=1` `STRATA_HC_DOWN_DP4A_MAX_T=6` 共 12 项未动 |
| 4 | 健康 | `/health` ok · restarts=0 · StartedAt `2026-11-07T14:33:49Z` |
| 5 | 资源隔离 | `ulimit -l` unlimited · `memlock=-1:-1` · `VmLck 0 kB` |
| 6 | 显存 | **VRAM free 849,211,392 B（0.79 GiB）**；expert cache 8301 槽 / 24.23 GiB；borrows 2609 槽 |
| 7 | 回滚件 | `attn`（`3b758f88…`）+ `kvg`；备份 `tmp/w1047/cfg_preinstall_w1047.bak`；rollback = 恢复 config 并重启容器（≈45 s） |
| 8 | 本轮改动 | **零**：disk = build = running；**重启 0 次 / 0 分钟停机 / 装机 0 / 回滚 0** |
| 9 | ROCm 版本 | 打包 .info/version 10.1.0；HIP 7.16.26323；clang 24 · `--offload-arch=gfx906` |
| 10 | llama.cpp 版本 | b12180 = `bcb0152876e8f0b684ba70d3defcab6cdf35adb5` + `mmq*` @ `4c1004c49221b07c3b8108977e3d1991fc9f45cc` |

**二、主线** — `gfx906/mi50` @ e181bda5（`mi50-0.2.11-r33-14-2-ge181bda5`）；生产树 `pr/k10`，领先 2 / 落后 0 / 脏 0 行。本轮新增 origin ref：`ci/retro/*` **10 条**（按历史 sha 回溯的 CI 分支）。`ci/w1047-coverage @ 6213fcb87` 仍在；本轮自身工具改动将再追加一个 provenance 提交并补 CI run（同 W1047 手法，见下）。

**三、本次落生产** — **零**：重启 0 次、0 分钟停机、装机 0、回滚 0。本轮全部是回溯、账与门；任何未来装机从 `tools/deploy_gate.py:361`（D7）起多一道机械拦截。

**四、进度** — **485 条 / 已结 391 / 80.6%**。新增 `P534`（回溯执行）、`P535`（D7 硬门）、`R113`（mmq 二段择机移植）。

队列：**R113（mmq 二段：#30837 首选）** → **R110/R112（k8v4 PV-dot8 真实 P/V dump）** → **R111（GPU self-hosted runner）** → **R109（A1 exact DPP / A5 解除死派发）** → **R106（gen_config 对齐）** → **R105（gfx906 能力清单）** → **R107（audit 欠账 17 轮）**。

## 1. 复核五条 → 权威调优方案对照（全部已入 `deploy/W832_OPT_PLAN_V2.md`）

| 引文条目 | 权威落点 | 本轮动作 |
|---|---|---|
| ① R103 移植面 | `R109`（B3 hc4b 已装机；A1/A5 待开）+ `P523` B2 死路径纠正 | 无新增移植（B3 已在 W1047 落地）；对照表写入方案 |
| ② dot4 硬件主力 | 方案 dot4 段（`include/strata/platform/hip_compat/strata_hip.h:237` 硬件 / `:246` 软回退；逐 TU 计数） | `fused_gr` 真空已由 B3 填（720 条 dot4） |
| ③ dot8 三步走 | `R91`+`R74`+`R110/R112`（k8v4 PV-dot8 预注册） | 不动；R110 合成上限 1.483×/rel-rms 6.23% 待真实 P/V |
| ④ mmq 升 pin | `P520` + **新立 `R113`** | **GitHub API 逐条核实**（下节） |
| ⑤ CI/CD 缺口 | `P521`、`P529–P532` + **本轮 `P534/P535`** | 从清单变执行（下节） |

## 2. mmq 的 5 提交清单——网上核实，不猜（`R113` 输入）

`ggml/src/ggml-cuda/mmq.cuh` 在 pin 点 `4c1004c4`（#30553，10-19）之后恰有 5 个提交（API 逐条）：

1. `1a24df16`（10-23，**#30837** DP4A MMQ tile height 为 warp 整数倍）——wave64/gfx906 直接相关，**首选移植**；
2. `c49edf09`（10-25，#29948 FFN gate/up + GLU 融合）；
3. `eb4e244b`（10-29，#31373 RDNA4_M 家族）——gfx906 无关；
4. `5ce06fc7`（11-05，#31296 NVFP4 gate/up 融合）；
5. `69ee2ecc`（11-05，#31047 MoE 数据布局线性化）。

上游 `get_J_best()` 在 `ggml/src/ggml-cuda/mmq.cu`；本树 `moe_mmq.cu:386 pick_J()` 自己遍历。这些只入方案与 `R113` 队列，**本回合不换 mmq**（换则必重编 + 数值门 + A/B）。

## 3. 历史变更 CI/CD 回溯——执行结果（`P534`）

**覆盖口径**：所有产生过二进制/曾装机的变更 sha 都必须有 Downstream gate run，或显式豁免行。结果：

- **14 个项目提交**（port-all 7 + lcpp-k10 2 + attn/dot48/hc-dp4a 5）与 **4 个 ci 提交**：全部 `run=success`。
- 缺 run 的 **10 个 ref** 本轮补 `workflow_dispatch`，全部绿（run 42384609225–42385018433 段）：

| ref | sha | run |
|---|---|---|
| `ci/retro/fa8e6761-k10-pin` | `fa8e67618421…` | 42384965137 |
| `ci/retro/79516b21-pa0` | `79516b21ca5d…` | 42384971336 |
| `ci/retro/8b44f3d1-pa1` | `8b44f3d1097b…` | 42384976042 |
| `ci/retro/806a4b2f-tqfix` | `806a4b2f6288…` | 42384981158 |
| `ci/retro/3b935ddf-pa2land` | `3b935ddfcc8d…` | 42384985902 |
| `ci/retro/8b5e547f-pa3` | `8b5e547fa64f…` | 42384990467 |
| `ci/retro/62d10e25-pa5` | `62d10e25cfb0…` | 42384995266 |
| `ci/retro/91a7c5a4-pa6pa7` | `91a7c5a4e284…` | 42385018433 |
| `ci/retro/064aa6c0-hc-first` | `064aa6c0451a…` | 42385005419 |
| `ci/retro/pa4-recon` | `e36f0889c7ba…` | 42384609225 |

**三个「未提交补丁」的精确处置**（比旧账更准）：

- **pa4**：`pa4_patch.py`（构建时脚本本身）在 `8b5e547f` 上逐字重建 → `ci/retro/pa4-recon@e36f0889`，CI 绿。证据级 B+（补丁与 base 都是构建输入）。
- **pa7**：旧账写「62d10e25 + pa7 未提交补丁」不完整——工作树是**累积**的。按 `pa6_patch.py → wire_f16d.py → pa7_patch.py` 三连在 `62d10e25` 重放，结果与已提交 **`91a7c5a4` 逐字节相同**：pa7 的构建树内容就是 `91a7c5a4`，该 sha 的 run 42385018433 即覆盖。
- **pa2**：`wire_opt_prefill*.py` 的锚点与任何已提交态都对不上，精确树判**不可恢复**；登记豁免，内容落点=`3b935ddf`（run 42384985902）。不硬凑重建。

**永久豁免（不抹掉的事实）**：UNTRACKED 43 件（`strata-0.1.53`–`0.1.56*`，源 sha 未知，md5 保留可验尸，仅回滚用）；`strata-0.1.57-010`（0.9.0 树 / sha 未记录，P390 反例）。

## 4. 覆盖账与 D7 硬门（`P535`）

- **`deploy/CI_RUNS.tsv`**：唯一 CI 覆盖账（sha → run_id/status/artifacts/豁免原因），装机证据从「口头说跑过」变成可 grep 的表。
- **`tools/deploy_gate.py` 新增 D7**：装机 exe 的构建 sha 必须 `run=success` 或有显式豁免行；**表缺/行缺 = REFUSE 而不是 SKIP**（吸取 W1043「SKIP 当 PASS」的教训）。负向自测 **14/14**（含 D7 三例：命中/无行拒/表缺拒）。
- **`artifact_ledger.tsv`**：回填 14 件 run 绑定；修正 pa2/pa5/pa7 装机注记（pa5=`62d10e25` 提交；pa7=`91a7c5a4`；pa2=豁免+内容落点）。

落点可复核：D7 实现在 `tools/deploy_gate.py:361`（`ci_run_ok` 在 `tools/deploy_gate.py:127`）；覆盖账是 `deploy/CI_RUNS.tsv:1`；pa7 三连重放脚本链 `albus/w1039/pa6_patch.py:1` → `albus/w1039/wire_f16d.py:1` → `albus/w1039/pa7_patch.py:1`；pa4 重建 `albus/w1039/pa4_patch.py:1`；回溯编排 `albus/w1048/retro_ci.py:1`/`retro_b2.py:1`；artifact 账 `albus/w1047/bundle/stage/ci/provenance/artifact_ledger.tsv:1`；方案对照 `deploy/W832_OPT_PLAN_V2.md` 的「复核五条 → 权威落点对照」段。

## 5. 纠错与边界

**纠正上轮/旧账三处**：①「pa5 提交」不是无名提交，就是 `62d10e25`（`commit_pa5.sh` 逐字）；② pa7 不是单补丁，是 pa6+wire_f16d+pa7 三连且= `91a7c5a4`；③ 上轮说「pa4/pa7 未提交」——pa4 由本轮重建为可 CI 的提交，pa7 的内容其实早已提交。

**工程教训**：dispatch 轮询被 GitHub 502 打断 ≠ run 失败（8 个已绿），补轮询收齐即可；sha 匹配必须长短双向前缀（首轮 D7 对在产件误报缺行，自测没覆盖到该形态，已修）。

**不冒充完成**：`R111` GPU self-hosted runner 仍 0（编译/数值/装机仍是 166 手工窗口）；`R110/R112` 真实 P/V dump 未测；`R113` mmq 二段未实施；`R107` `audit_scope` 仍 FAIL（17 轮连续未审）。本轮零停机零装机。

门状态：报告三门 / 方案 / 账本 / 指针 / param_pair / claim_homes / round_ledger / handoff / recipe / binary_integrity 全 PASS；`deploy_gate --self-test` 14/14。唯一 FAIL 仍为既存 `audit_scope`。
