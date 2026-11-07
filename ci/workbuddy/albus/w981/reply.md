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

改动 **0**；重启 **0 次**；停机 **0**。回滚命令同上（本轮机不可用场景不需要）。

## 四、进度 + 队列

**176 条 / 已结 102 / 58.0%**；主线 **148 / 102**；死块池 **0/28**。
队列：**R88 → R86 → R87 → R46 → R91 → R93 → R72 → R81 → R79/R80 → R63/R60/R64**。

---

## 五、当前基线 vs 昨天（同条件：同一探针、冷读、唯一前缀、同长度）

| 长度段 | 昨天（11-04 CST） | 今天（11-05 02:13） | 差 | 判读 |
|---|---:|---:|---:|---|
| **2.35K** | 523.7 / 524.0 | **531.4 / 546.6** | **+1.5% ~ +4.3%** | 持平偏正 |
| **59–60K** | 804.1 @60,330；752.6 @60,201（同日）；794.4 @59,054 | **791.7 @59,059** | **−1.5%（对 804）／+5.2%（对 752）** | 落在昨天的自身散布内 |
| 130K | 789.6 @130,105 | 784.0 @127,556 | −0.7% | 持平 |

**必须说清的口径问题**：昨天同一长度段（60K）自己在 **752.6–804.1** 之间摆了 6.8%，这是生产请求（内容不同、专家命中不同）的固有散布，不是我改出来的。所以：

- 2.35K 的两组今天各自 531.4 / 546.6，**自身就差了 2.9%**；
- 真正能判的是**同探针、同内容模式**的对子：2.35K +1.5~4.3%、59K −1.5%，都 < 2×CV（≈6%）。

⇒ **结论：升级 v0.9.0 + PLE 改 mmap + NVMe 内核策略之后，与昨天同条件持平，没有退化。**

## 六、有一个"看起来变快"的信号，但我先不认领

日志里 15K 段：昨天 704.4 / 714.4 / 711.4，今天 **780.3**（+9.5%）。看着像提升，但这两组不是同条件：

- 昨天的 704–714 是 **05:34–05:52 UTC（13:34 CST）**，此时引擎还是 0.4.1/0.8.0、磁盘还是 SATA、PLE 还是 `ram`；
- 今天的 780.3 是 v0.9.0 + NVMe + `mmap`；
- 而且它们是**生产请求**，内容不同、专家命中不同。

⇒ 归因为"环境/版本一起变了"可以，但**不能算作某一项改动的收益**。要认领，得用 `cfg_apply` 在现役基线上做单变量 A/B。

## 七、下一步

1. 已记入门的账本：`ci/cfg_apply.py --label p4-base2 --record-only --n 5` → **decode 34.94 (CV 7.91%)、TTFT 3.891 s (CV 0.52%)**，作为后续 A/B 的对照（`ci/state/cfg/p4-base2.json`）；
2. **P4-d2**：`--pcie-frac 0.35`，走 `cfg_apply`，判据仍是 2×CV，不过自动回滚；
3. 15K 段那 9.5% 若要归因，单独立项（同内容/同探针、NVMe 前后各一次），不并进本轮结论。
