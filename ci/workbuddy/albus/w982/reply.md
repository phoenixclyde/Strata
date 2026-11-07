## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `49bf0c812fe5e53db4a00b5be97e3a13`；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-04T17:59:16Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **零改动**（纯测量）；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `3c663620` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 10** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **0 次**；停机 **0**。回滚命令同上。

## 四、进度 + 队列

**176 条 / 已结 102 / 58.0%**；主线 **148 / 102**；死块池 **0/28**。
队列：**R88 → R86 → R87 → R46 → R91 → R93 → R72 → R81 → R79/R80 → R63/R60/R64**。

---

## 五、完整基线对比表（prefill + decode，按 engine 启动切段）

**prefill 单位 tok/s（冷读、`reused=0`）；decode 128 列为同一探针（128 token、唯一前缀、冷启动）。**

| 时点(CST) | 引擎 | 磁盘 / PLE | 2K | 8K | 16K | 32K | 60K | 130K | decode@128 | 窗口 ms | 可比性 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 11-04 12:47 | `0.1.56` | SATA / `ram` | – | – | – | – | **802.2** | – | – | 42.0 | 昨天最好（生产请求） |
| 11-04 13:25 | `0.1.56` | SATA / `ram` | – | – | – | – | 751.2 | – | – | 31.4 | 昨天低值（同长度散布） |
| 11-04 23:24 | `-080` | NVMe / `ram` | **523.7** | – | – | – | – | – | – | 52.9 | 迁盘后 |
| 11-05 00:40 | `-090` | NVMe / `ram` | 488.9 | – | – | – | 793.4 | – | **41.4 / 41.9** | 39.5 | 换 v0.9.0 后 |
| 11-05 01:16 | `-090` | NVMe / **`mmap`** | 535.3 | 715.0 | **780.3** | 775.4 | 786.2 | **784.0** | – | 36.9 | 六档基线 |
| **11-05 02:22（当前）** | `-090` | NVMe / **`mmap`** | **531.4 / 546.6** | – | – | – | **791.7** | – | **43.14**（CV 3.3%） | 38.3 | 本轮实测 |

## 六、逐项判读

**prefill（同探针、同长度、冷读）**

| 长度 | 昨天 | 今天 | Δ | 判定 |
|---|---:|---:|---:|---|
| 2.35K | 523.7 / 524.0 | 531.4 / 546.6 | **+1.5% ~ +4.3%** | 持平偏正 |
| 59–60K | 802.2 / 751.2（同一天两个值） | 791.7 | **−1.3% ~ +5.4%** | 落在昨天自身散布内 |
| 130K | 789.2（11-04 08:19 段） | 784.0 | −0.7% | 持平 |

**decode**

- 同一探针对照（`-090`、NVMe，仅 PLE 模式不同）：`ram` 41.4 / 41.9 → **`mmap` 43.14（CV 3.3%）**，**+3% ~ +4%**，在噪声边缘、方向为正。
- **昨天（`-080`、SATA/`ram`）没有同形 128-token 探针**，所以不与今天硬比；昨天只有窗口指标（42.0 ms/window）。今天窗口 36.9–38.3 ms/window，看起来更小，但 **tokens/window 不同（spec 接受率随内容变）**，不能直接换算成 tok/s 的胜负。

**TTFT（2K，门账本记录）**：`p4-base` 3.948 s（CV 0.4%）→ `p4-base2` 3.891 s（CV 0.5%），−1.4%，稳定。

## 七、结论

1. **升级 v0.9.0 + PLE 改 `mmap` + NVMe 内核策略之后，prefill 与昨天同条件持平**（2.35K +1.5~4.3%，60K ±1.3~5.4%，130K −0.7%），全部落在 2×CV 内。
2. **decode 略有正向**（43.14 vs 41.4/41.9，+3~4%），但只有同一小时的对照，不足以当结论；要定性得跑一组 `ram` ↔ `mmap` 的 A/B（各 n≥5，同探针）。
3. **昨天的 60K 自己就在 751–802 之间摆（6.8%）**——这个量级决定了：任何 <7% 的"提升"都必须靠 A/B，不能靠跨天比。
4. 下一步：**P4-d2 `--pcie-frac 0.35`** 走 `cfg_apply`（判据 2×CV，自动回滚）；完成后连同 decode 的 `ram↔mmap` 对照一起给第二张表。
