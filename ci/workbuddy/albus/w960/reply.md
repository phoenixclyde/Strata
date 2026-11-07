## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细 | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、restarts=0、StartedAt `2026-11-04T11:06:42Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、`ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | 部署分支**零**；disk = build = running 三方一致（`ae085365…`）；实验分支 `exp/R90-080` 未合 |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag `mi50-0.2.10-r30` · 上游 `ffa80d73` · 落后 0 / 领先 39 · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；本轮为测量重启 **1 次**（B2），停机 **≈4.5 分钟**（脚本自动恢复）。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：**R88-量**（异步拷贝的 wait-copy 相位）→ **R86-A/B** → R87 → R46 → R91 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64 → R49 → R50 → R30′；R90 只保留"摘修复/当对照树"。

---

## 结论：0.8.0 的 prefill 慢 **6%**，R90 降级

| 臂 | 二进制 | prefill（tok/s） | 均值 | SD |
|---|---|---|---:|---:|
| A | `strata-0.1.56`（0.4.1） | 601.74 / 604.28 / 599.17 | **601.7** | 2.6（0.4%） |
| B | `build-080c/strata`（0.8.0） | 568.41 / 552.15 / 576.82 | **565.8** | 12.5（2.2%） |

**区间不重叠**（B 最大 576.8 < A 最小 599.2），Welch **t≈4.9**（p≈0.02）⇒ **−6.0%**；decode 持平 ~19.0 tok/s（A 有一次 40.36 的 2× 异常，正是 `W958` 那个不可复现的来源）。

## 先排除了两个"我们自己的错"

- **J 没选错**：加 `STRATA_MMQ_DEBUG_J` 实测，`pick_J` 对 **Q5_1(type=7) 与 Q4_K(type=12) 都给 J=64**，与 0.4.1 内部那段"tiles 最少且放得下"的循环**同解**。
- **精度参数没选错**：0.8.0 的 `get_prec_src1()` 对非 Blackwell-FP4 **恒返回 `GGML_PREC_Q8`**，与我们 27 处调用点一致。

构建开关逐项 diff 只剩三处不同：`STRATA_GGML_DIR`（就是要换的）、**`STRATA_MMQ_TQ_OVERLAY` ON vs OFF**、架构标记写法。⇒ **唯一未排除的混淆项是 overlay**，下一步补掉。

## 这意味着什么

`R90` 升第一的前提是"4 个 minor 的修正能换来收益"。现在：**tile 层逐字节相同**（`W955`），**prefill 实测 −6%**。收益看不到，代价是量出来的。

**改判（已写进 `W954` 与账本）**：R90 从第一位降为"**参考实现 / 按需摘取，不做整树上线**"；队列第一回到 **R88 异步分阶段拷贝**——它在我们这条基线上有同模型外证（pp8192 877→1978），而 `W955` 已证上游 0.8.0 **没有**那两个开关，升级也白拿不到。

## 下一步

① 补 trellis 的 `ggml_cuda_mmq_util_funcs(..., prec)` 适配 → overlay=ON 复测（消掉最后一个混淆项）；
② 六长度档 prefill（2K→130K，2048 token 只是单点，生产窗口是 600–1200 ms）；
③ 若 6% 稳定，按 hunk 定位 0.8.0 的 `mmq.cuh` 退步点，看有没有"上游修好而我们没有"的小点可以摘回来。

产物：`deploy/W960_R90_PERF_REGRESSION.md`；`W954` 已加改判横幅；账本 R90 仍 **INFLIGHT**（结论：不推进整树）；结案台账 39/39。
