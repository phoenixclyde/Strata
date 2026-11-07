## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T08:14:34Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | **零**；disk = build = running = `ae085365…` 三方一致 |

## 二、主线

`gfx906/mi50 @ 5f73cd15` · tag `mi50-0.2.10-r28` · 上游 `ffa80d73` · 落后 0 / 领先 37 · 工作树脏 0 行 · 与 origin 同点。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；重启 **0 次**；停机 **0 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：R90-S1 → R90-S2 → R88-量 → R90-S3 → R86-A/B → R87 → R90-S4 → R88-实现 → R46 → R91-P1/P3/P4 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64（只作验证）→ R49 → R50 → R30′

---

## 整改：做成机器可验，而不是再写一遍横幅

新增 **`deploy/AUDIT_LEDGER_A24.tsv`**（33 行：`id / 级别 / 文件 / 标志串 / 状态 / 处置 / md5`）+ **`tools/audit_closure.py`**：
逐条检查“撤回标志串是否还在原文里”。**后续任何人删掉一条撤回，脚本立刻 FAIL**。

```
closure: 33 rows | RESOLVED-verified 33 | FAIL 0 | WARN 0
```

本轮补的：7 件 P2 口径注记（W941/932/931/933/929/930/935）、W927 横幅、W942 结论级撤回、W944 的 −6.3% 改“0 ~ −6.3% 未知”。

**最该说的一条：审计自己错了一条。** `A24-12` 我采纳 `W948` 的「版本号不是可比锚点」，还断言 `get_J_max` 是自家补丁——**两个方向都反了**。所以本轮的第一件事不是审别人，是修自己。

## 版本锚点（钉死了，`W953`）

| 树 | LLAMA_VERSION | 与我们 |
|---|---|---|
| **我们** | **0.4.1** | = upstream **`e6ab7c1a4`**（2026-09-22），`mmq.cuh` **逐字节相同（diff 0，71,851 B）** |
| furnace | 0.4.1 基座 | **同基座** —— 它的 +41%/+80%/+126% 就是在这条基线上打补丁打出来的 |
| mx（`b11553`） | 0.6.0 | 比我们**新** 2 个 minor |
| exabit | 0.7.0 | 比我们**新** 3 个 minor |
| 上游 `b12099` / master | **0.8.0** | 比我们**新 4 个 minor** |

⇒ 上一轮「三家 fork 都比我们旧」是**反的**；`get_J_max` 是 0.4.1 时代的上游符号、后来被删（furnace 同基座但重写了 MMQ）⇒「**有它 = 更旧**」。
⇒ `R90` 从“方向成立、判据无效”变成**硬事实：落后 4 个 minor**，因此升为队列第一位。

## 方案重排（`W954`）

排序规则改成一条可执行的：**先按停服次数分档，档内按「期望端到端 × 证据系数（A1.0/B0.7/C0.4/外证同构0.6）」，带精度门的往后放一档。**

| 变化 | 内容 |
|---|---|
| **升** | R90 到第一位（版本锚点钉死后，期望从“未知”变成“4 个 minor 的 qwen4exp/GDN/QSA 修正”） |
| **升** | R88 到第二位，且**先做零停服的“量”**（读 0.8.0 调度器 + 从日志取 wait-copy 绝对 ms） |
| **降** | R86 到第三，并明写预期 **0 ~ −6.3% 未知**；排序理由改成“最便宜 + bit-exact”，不是“预期最大” |
| **并** | R84 并入 R91 的 P0（同一件事，避免双记） |
| **降** | R85 只作验收口径（801→≥850），不占队列位置 |
| **新** | **R93**：0.8.0 上线后**重标 chunk** —— 16384 的倒 U 顶点是在 0.4.1 上测的，升级后路径变了，顶点可能移动 |

## 上网核实的一条硬结论

上游 0.8.0 的 `ggml/src/ggml-backend.cpp`（112 KB）与 `src/llama-context.cpp`（179 KB）里，
`INPUT_STAGE` 与 `ASYNC_INPUT_MIN` **各 0 命中** ⇒ furnace 那套“异步分阶段拷贝”（pp8192 877→1978）**不在升级里**，
`R88` 必须自己写。好处是 furnace 与我们**同基座**，它的调度器改动可以直接对照。

产物：`deploy/W953_VERSION_ANCHOR_AND_SELF_CORRECTION.md`、`deploy/W954_PLAN_RERANK.md`、
`deploy/AUDIT_LEDGER_A24.tsv`、`tools/audit_closure.py`；方案表 `W832@05400e73` 已按新队列重写。
