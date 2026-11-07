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
| 8 | 本轮改动 | 生产**零**；主线新增 1 个提交（`ci/config.sh`，见下）；disk = build = running = `ae085365…` |

## 二、主线

`gfx906/mi50 @ 03381d82` · tag **`mi50-0.2.10-r29`**（末条 tag == HEAD）· 上游 `ffa80d73`（v0.2.10）· 落后 0 / **领先 38** · 工作树脏 0 行。

## 三、本次落生产

改动 **零**；回滚命令 `cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`；重启 **0 次**；停机 **0 分钟**。

## 四、进度 + 队列

**176 条 / 已结 101 / 57.4%**；主线 148 / 101 / 68.2%；死块池 0/28。
队列：**R90-S3**（修 overlay 锚点 + mirror + 逐位）→ R90-S4（上线 A/B）→ R88-量 → R86-A/B → R87 → R88-实现 → R46 → R91-P1/P3/P4 → R93 → R72 → R81 → R79 → R80 → R63/R60/R64 → R49 → R50 → R30′

---

## 本轮做的：R90 的 S1 / S2（零停服）

**S1 完成**：0.8.0 的 `ggml/` 已 sparse-clone 到 `ref/llama_b12099`（28 MB）。

| 项 | 结果 |
|---|---|
| `ggml-cuda` 文件数 | 我们 **161** → 0.8.0 **168**（+`gated-delta-net-mma`、+`top-k-mask`、+`conv3d`、+`batch-get`，−`fattn-swizzle.cuh`） |
| `ggml` 版本 | 0.24.0 → **0.28.0** |
| **`mmq-config-gcn.cuh`** | **逐字节相同（281 行，diff 0）** |
| mirror 钩子 | `mul_mat_q_process_tile` 4→4、`DECL_MMQ_CASE` 23→**26**、`load_tiles_q5_1` 3→3、`vec_dot_q4_K` 1→1 |
| 文本差 | `mmq.cuh` 585 行 · `mmq-load-tiles` 322 · `mmq-vec-dot` 93 · `vecdotq` 189 |

⇒ **GCN tile 表这 4 个 minor 没动**，所以「tile 层没空间」那批结论不因升级失效；但 `R86`/`R91` 要改的两个函数**行号全变了**。

**S2 通过**，但暴露一个必须记的坑：

```
-- trellis MMQ overlay off: anchor not found:   GGML_TYPE_COUNT   = 43,
-- Configuring done (4.6s)   CFG_RC=0
```

0.8.0 里这个枚举是 **44**，于是 overlay 脚本**打一行日志就整体跳过**——**configure 照样返回 0**。
它是"静默降级"：构建成功、少了 trellis 的 MMQ 实例。我们不用 trellis（专家是 Q4_K/Q5_1/Q8_0）⇒ 对当前模型无害，
但任何人看到"配置成功"都会以为 overlay 生效了。S3 要把它改成**锚点不命中就 FATAL_ERROR**，不许静默。

编译实跑：`mmq-instance-q4_k.cu.o` 与 `-q5_1` 两个实例 **24.1 秒**编过。

| 对象 | 0.4.1 | 0.8.0 | 差 |
|---|---:|---:|---:|
| `mmq-instance-q4_k.cu.o` | 973,544 B | **1,128,104 B** | **+15.9%** |
| 其中 `.hip_fatbin` | 701,280 B | **777,960 B** | **+10.9%**（md5 也不同） |

⇒ **机器码确实变了**。"编过"只证明可移植，**不证明等价、更不证明更快**——所以 S3 的逐位测试与 S4 的 A/B 一个都不能省。

## 顺手修掉一条审计遗留（`AUDIT24` P1）

`ci/config.sh` 一直指着 **gfx029-build / 0.2.9-101**，而生产是 **build-r28 / 0.2.10-101**（W938 改了流程没改它）——
跑 `ci/strata-ci build` 会拿错 ninja 树与镜像。已改、已提交 **`03381d82`**、已重打 tag **`mi50-0.2.10-r29`**（保 provenance）。

## 结案台账

`tools/audit_closure.py`：**35 行 / RESOLVED 35 / FAIL 0 / WARN 0**（新增两条：`ci/config.sh` 修复、S1/S2 可行性）。

## 下一步（S3 的判据先写死）

① overlay 在 0.8.0 上必须打印 applied N/N，不许静默 off；② 同 prompt 贪心前 64 token 的 argmax 序列与 0.4.1 相同；
③ 六长度档 `0 reused`、`|Δ| ≥ 2×CV`；④ decode 劣化 >2×CV 直接回滚。

产物：`deploy/W955_R90_S1S2_FEASIBILITY.md`；账本 R90 → **INFLIGHT**；`ref/llama_b12099` + `build-080` 留作 S3 的输入。
