## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `ae085365441381c438b56bcabcccf450`，42,924,432 B，`strata 0.1.56` |
| 3 | **config** | md5 `24d66f6a86d7b75f58015efa38d462d2`；exe=`/data/bin/strata-0.1.56`；**args 33 条**；**env 9 条** |
| 3a | args 明细（33） | `--pack /data/packs/ud-q4_k_xl` `--native …UD-Q4_K_XL-00001-of-00004.gguf` `--expert-profile /src/data/expert-profile.bin` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp /data/mtp/rt` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save /data/profiles/q4kxl-learned.bin` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` |
| 3b | env 明细（9） | `HSA_OVERRIDE_GFX_VERSION=9.0.6` `STRATA_PREFILL_CPU_SHARE=auto` `STRATA_PREFILL_CPU_SHARE_MAX=3072` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING=/data/gfx906-rocblas-5.7.0.txt` `STRATA_GFX906_TUNED=1` `STRATA_CKPT_MOVE_PARK=1` `STRATA_DECODE_TIMING=1` `STRATA_SPEC_DEPTH=1` |
| 4 | 健康 | `/health` status=ok、restarts=0、StartedAt `2026-11-04T07:09:33Z`、max_context 262144 |
| 5 | 资源隔离 | `ulimit -l = unlimited`、`VmLck 28,125,140 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 slots (7.62 GiB)`、`VRAM free 882 MiB` |
| 7 | 回滚件 | 容器 `strata166-407.pre-210`、引擎 `strata-0.1.55w`、命令 `ci/strata-ci rollback --exe strata-0.1.55w --apply` |
| 8 | 本轮改动 | **零**；disk = build = running = `ae085365…` 三方一致 |

## 二、主线（6 项）

`gfx906/mi50 @ 5f73cd15` · tag `mi50-0.2.10-r28` · 上游 `ffa80d73`（v0.2.10）· 落后 0 / 领先 37 · 工作树脏 0 行 · 与 origin 同点。

## 三、本次落生产（4 项）

改动：**零**。回滚命令：`cp /data/strata-huihui-ud-iq4_xs.json.bak_w941 …/strata-huihui-ud-iq4_xs.json && docker restart strata166-407`。重启次数：**0 次**。累计停机：**0 分钟**。

## 四、进度（4 项 + 队列）

**173 条 / 已结 101 / 58.4%**；主线 145 条 / 101 / 69.7%；死块池 0/28。
队列（有序）：R88（异步拷贝）→ R86（Q5_1 repack）→ R87（q8_1 复用）→ R85+R46（attn 效率）→ R64（Q·K int8）→ R72（reserve 600）→ R81 → R79 → R80 → R49 → R50 → R30′；并行 INFLIGHT/OPEN：R84（dot8 移植）、R60、R63、R89。
