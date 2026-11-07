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
| 8 | 本轮改动 | 生产**零**；主线 +1 提交（overlay 锚点）；disk = build = running = `ae085365…` |

## 二、主线

`gfx906/mi50 @ 55a1acd4` · tag **`mi50-0.2.10-r30`**（末条 tag == HEAD）· 上游 `ffa80d73` · 落后 0 / **领先 39** · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；重启 **0 次**；停机 **0 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：**R90-S4**（逐位 + 六长度档 A/B，需 1 次停服）→ R88-量 → R86-A/B → R87 → R88-实现 → R46 → R91-P1/P3/P4 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64 → R49 → R50 → R30′

---

## 本轮：0.8.0 能编、能链、能跑

分支 `exp/R90-080`（worktree），**部署分支与生产一行未动**。

**三道坎，全是 API 变更，没有算法问题：**

| # | 差异 | 我们怎么改 |
|---|---|---|
| 1 | `ggml_cuda_mmq_get_config(...)` 多了第 5 参 `ggml_prec` | 7 个调用点补 `GGML_PREC_Q8` |
| 2 | `mul_mat_q_case<T>` 模板多了 `prec_src1` | 27 个调用点补 `, GGML_PREC_Q8` |
| 3 | `ggml_backend_cuda_context::new_pool_for_device` 从两参改成三参静态成员 | 1 行签名 |

上游自己的 dispatch 就是 `mul_mat_q_case<GGML_TYPE_Q4_0, GGML_PREC_Q8>`，我们的激活是 Q8_1，照抄不多想。

**结果：**

```
[24/24] Linking HIP executable strata     0 error
-rwxr-xr-x 39599200  build-080c/strata
$ ./strata --version      -> strata 0.1.56     RC=0
$ ./strata serve --help   -> 286 行            RC=0
```

改动规模 `git diff --stat`：**6 个文件、+35 / −35 行（零净增）**。⇒ 「换基线要改多少」这个问题，答案从"未知"变成"三十几行"。

## 顺手修掉的"静默降级"（提交 `55a1acd4`，tag r30）

`cmake/strata_ggml_tq_overlay.cmake` 把锚点写死成 `GGML_TYPE_COUNT   = 43,`，0.8.0 里是 44 ⇒ **打印一行就整体跳过，configure 仍返回 0**。已改成按枚举名匹配（取上游的值），并在真套不上时 `FATAL_ERROR`（除非显式 `-DSTRATA_TQ_OVERLAY_SOFT=ON`）。验证：改前 `overlay off`，改后 `overlay on`。

**另一条要记的**：overlay 的 **trellis 段本身**也要适配 0.8.0（`ggml_cuda_mmq_util_funcs` 构造多了 `prec`）。trellis 不在我们模型里，所以本轮 A/B **显式** `-DSTRATA_MMQ_TQ_OVERLAY=OFF`——是"明确关掉"，不是"静默没了"。

## 下一步（S4，需要停服一次）

① **逐位**：同 prompt 贪心前 64 token 的 argmax 序列，0.4.1 vs 0.8.0 比对（`mmq.cuh` 改了 585 行、fatbin +10.9%，不保证逐位相同）；
② **A/B**：六长度档、`0 reused`、`|Δ| ≥ 2×CV`，decode 只守不劣化；
③ 成本：停服 ≈4 分 20 秒 + 测量 40–60 分钟；回滚只是 `STRATA_GGML_DIR` 指回旧树。

产物：`deploy/W956_R90_S3_MMQ_API_PORT.md`；分支 `exp/R90-080`（35 行改动，未合）；账本 R90 仍 **INFLIGHT**；结案台账 36/36。
