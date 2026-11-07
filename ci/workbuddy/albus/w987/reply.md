## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `7a1cab853ff102c9d11ec9e662e83fe9`；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 8** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` `--vision` `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-04T19:06:09Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | 生产配置**净零改动**（chunk 实验已回退）；账本 12 处；门加 `--lengths`；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `33bddcfd` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 14** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**（chunk 8229 臂被判否并自动回退）；**重启 3 次**（基线 1 + 臂装 1 + 回退 1），各 ≈45 s，**停机合计 ≈2.5 分钟**；回滚件同上。

## 四、进度 + 队列

**184 条 / 已结 111 / 60.3%**；主线 **156 / 111**；死块池 **0/28**。
队列：**R88 → R89 → P239 → P244 → P48 → P33 → R91 → R86 → R87 → R46**。

---

## 五、整改清单：审计输出逐条落地（12 项）

| 轴 | 项 | 整改 |
|---|---|---|
| 参数册 | 11 条 ADOPTED env 生产里没有 | 全部标注 **default-on（二进制默认开）**，口径不再要求 env 出现 |
| 参数册 | P65 死参 | → **CLOSED**（生产已删，env 9→8）+ 新增 P256 记录清理 |
| 参数册 | P10 册值 `auto` vs 生产 `auto:16384` | 值更正 |
| 参数册 | P107 册值 rocBLAS 5.5 vs 生产 5.7.0 | 值更正 |
| 参数册 | P227 auto 候选 | → **REJECTED**（实测不显著）+ 新增 P257 |
| 账本 | R84 INFLIGHT 陈旧 | → **BLOCKED**，写明解除条件（dot8 微基准） |
| 账本 | P2 BLOCKED 无解除条件 | 补：并发轴已关（W829），无对照则不可做 |
| 账本 | 15 轮动过生产无台账行 | 新增 P260（NVMe/分层）、P261（v0.9.0 基线）、P262（门加固） |
| 账本 | R93 未审 | → **DONE**（本轮实测结案）+ P263 |
| 门 | 只测 2K TTFT，看不到长度相关变化 | 新增 `--lengths`，每长度 CV 0.05–1.3% |
| 门 | 删参数无入口 | 新增 `--unset-env` / `--unset-arg` |
| 门 | 基线与臂重启状态不同 | 新增 `--restart-baseline`（W986 已加） |

## 六、R93 结案：chunk 16384 是对的，8K 不是缺陷

| 长度 | 16384（现役） | 8192 | Δ | 带宽 |
|---|---:|---:|---:|---:|
| 2K | 511.73 | 511.96 | +0.04% | 1.0% |
| 8K | 704.32 | 705.73 | +0.20% | 0.46% |
| **16K** | **774.74** | **730.20** | **−5.75%** | **0.42%** |

⇒ 门判 **ROLLBACK**，已自动回退。**8K 的 704 不是 chunk 缺陷**：`t=1.3+n/785` 预测 11.44 s，实测 11.30 s，就是那 1.3 s 固定成本在摊销——它属于 R88，不属于 chunk。

## 七、方案 V3.1（`deploy/W986_PLAN_V3.md` 已更新）

**收缩到一件事**：R88（首块重叠）。其余候选按成本排在其后。

| 序 | 项 | 预期 | 判据 |
|---|---|---|---|
| 1 | R88-1 首块分阶段计时 | 无收益，唯一前置 | 打出 CPU/GPU 每段耗时 |
| 2 | **R88-2 首块预取原型** | TTFT 2K 4.07 → **≤3.0 s** | −20% 以上且 2K/8K/16K 都不退化 |
| 3 | P239 `STRATA_PF_MMVQ` | 仅 100–250 token；需先加短长度探针（当前最短 2K） | 128/256 n≥10 |
| 4 | P244 `STRATA_GR_V3` | 先 bench ≥10% 才停服 | 微基准 |
| 5 | P48 `--pcie-mode dma` / P33 `pin=N` | 未量化 | n=10 |

**判据收紧**：prefill 类改动一律看三档（2K/8K/16K），任一档掉出 2×CV 即回退；decode/TTFT 只作副证。

## 八、下一步

1. **R88-1**：给 prompt 路径加分段计时（只加输出、不改行为），拿到首块的 CPU/GPU 分解；
2. 依分解决定预取实现（对齐 llama.cpp #28414 的“提前一个 split”与社区 fork 的“第二流预取 +6~64%”）；
3. `--vision` 仍等你一句话：用就留，不用则删（省 VRAM 与一条代码路径）。
