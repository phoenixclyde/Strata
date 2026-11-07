## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `49bf0c812fe5e53db4a00b5be97e3a13`（与实验前**逐字节相同**）；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 9** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_RESIDENT_HEADROOM_GIB=0.5` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-04T18:39:29Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | **生产配置零净改动**（pcie-frac 试验后回退到 0.20）；代码面 3 个门修正；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `e0b975d8` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 12** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；重启 **6 次**（4 个臂 + 2 次自动回滚/恢复），各 ≈45 s，**停机合计 ≈4.5 分钟**。所有臂都已回到 `49bf0c81…`。

## 四、进度 + 队列

**176 条 / 已结 102 / 58.0%**；主线 **148 / 102**；死块池 **0/28**。
队列：**R88 → R86 → R87 → R46 → R91 → R93 → R72 → R81 → R79/R80 → R63/R60/R64**。

---

## 五、本轮实验：三个臂，两个被否，一个暴露门的缺陷

| 臂 | 对照基线 | decode(tok/s) | TTFT 2K(s) | 判定 |
|---|---|---:|---:|---|
| d1 `--pool-tasks 6` | p4-base（**未重启**） | 32.85 | 4.1005（+3.87%，band 0.80%） | ROLLBACK |
| d2 `--pcie-frac 0.35`（n=5） | p4-base2（**未重启**） | 35.04 | 4.0585（+4.29%，band 1.04%） | ROLLBACK |
| d3 `--pcie-frac 0.10`（n=5） | p4-base2 | 37.65 | 4.0618（+4.38%） | ROLLBACK |
| **d0 空操作（同值重启）** | p4-base2 | 35.08 | **4.1134（+5.70%）** | **对照：比两个真臂还差** |
| base3（**重启后**基线） | — | 37.37（CV 3.56%） | 4.0743（CV 0.59%） | 新基线 |
| d2b `0.35`（n=5） | base3 | 34.80 | 4.0132（−1.50%，band 1.18%） | KEEP（旧策略） |
| d3b `0.10`（n=5） | base3 | 37.34 | 4.1004（+0.64%） | KEEP（旧策略） |
| **d4 `0.35`（n=10）** | base3 | 36.67（CV 5.84%） | **4.0527（−0.53%，band 2.24%）** | **REVERT（不定）** |

**两条硬结论**：

1. **d2/d3 的 +4% 是"重启"的代价，不是 pcie-frac 的效应**——空操作臂（把 0.20 改成 0.20 再重启）+5.70%，比两个真臂都差。
2. **n=5 会出假阳性**：同一改动在 n=5 时读作 TTFT −1.50%（越带宽），n=10 时变成 −0.53%（带宽 2.24%，不显著）。
   ⇒ **pcie-frac 0.10 / 0.20 / 0.35 在本机无差别，维持 0.20。**

## 六、门因此又修了三处（都是跑出来的，不是想出来的）

| 缺陷 | 现象 | 修法 |
|---|---|---|
| 基线与臂的**重启状态不同** | 空操作臂也"退化 5.7%" | 新增 `--restart-baseline`：基线也先重启，两者同一状态 |
| **中性即 KEEP** | `0.10` 无证据却被留在生产 | 判定改为三分：退化→ROLLBACK、提升→KEEP、**不显著→REVERT** |
| 恢复已知 good 值被当成实验 | 恢复 0.20 会因"无提升"被回退 | 新增 `--force-keep`（恢复操作不适用 A/B 判据） |

三次提交：`7ee33b02`（restart-baseline）、`e0b975d8`（三分判定 + force-keep）、`ccdc2c5b`（早先的 cfg_apply）。

## 七、P4 收口：R88 立项，靶子改了但方向得到外部证据支持

**我们的观测**（本轮）：303 token 请求，GPU 从 t+0.36 s 起 100% 忙到结束、CPU 同时 11–13 核满载；首块 **5.4 ms/token**，16K 稳态 **1.28 ms/token**（差 4.2×）。`--prefill` 借用量 7.62→3.11 GiB 无影响，`pool-tasks`、`pcie-frac` 均无效。

**外部证据**（本轮检索）：

| 来源 | 结论 |
|---|---|
| llama.cpp **#28414**（open） | "调度器在消费该 split 之前才上传每个专家张量，单上下文时**上传不与计算重叠** ⇒ 长 prompt 的 TTFT 被这段串行上传主导"；提议改为**提前一个 split 在第二流上传** |
| llama.cpp-tuning（社区 fork） | `GGML_CUDA_REGISTER_HOST=1`（pin 住 mmap 的 CPU 专家）+ `GGML_SCHED_PREFETCH_EXPERTS=1`（第二 CUDA 流预取下一层）⇒ prefill **1143 → 1880 t/s（+64%）**，输出 token 级一致 |
| ktransformers（SOSP'25） | expert deferral：CPU 算第 L 层专家与 GPU 算第 L+1 层 attention 重叠 ⇒ decode **+33%**；长上下文按层 prefill ⇒ 16K–64K **7–9×** |

**R88 定义（更新）**：不是"异步拷贝专家 blob"，而是**首块重叠**——让 CPU 出专家的第一段与 GPU 的首段计算并行。落地顺序：

1. 先做**可观测**：prefill 分阶段计时（现在只有 decode 有 `decode timing`），否则改完无法判断；
2. 再做**预取**：按 `--expert-profile` 的热度，在请求解析阶段预先把首块要用的专家推进 VRAM（对应外部 #28414 的"提前一个 split"）；
3. 成功判据：TTFT 2K 4.07 s → **≤3.0 s**，且 decode 不变；token 级一致优先，允许 `--spec` 关闭做对照。

## 八、下一步

1. R88 第 1 步（prefill 分阶段计时）——纯观测，无行为变更；
2. 第 2 步预取原型，走 `cfg_apply` 的判据（n≥10、2×CV、不显著即回退）；
3. 台账新增两行：`pcie-frac 双向无效`（DONE_NEG）、`pool-tasks=6 无效`（DONE_NEG）。
