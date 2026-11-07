## 一、生产容器（8 字段）

| # | 项 | 值 |
|---|---|---|
| 1 | 容器 / 镜像 | `4f387a12e84b` / `strata-gfx906:0.2.10-101`（image `5267df6dbdeb`） |
| 2 | 运行中引擎 | `eea5ea3749ad54b124330386605a18bc`，44,908,992 B（strata 0.1.56，v0.9.0 基线） |
| 3 | **config** | md5 `7a1cab853ff102c9d11ec9e662e83fe9`；exe=`/data/bin/strata-0.1.56-090`；**args 35**；**env 8** |
| 3a | args 明细 | `--pack` `--native` `--expert-profile` `--expert-cache auto` `--pcie-frac 0.20` `--spec 4` `--spec-min-p 0.70` `--mtp` `--max-context 262144` `--kv k8v4` `--prefill auto:16384` `--prompt-cache-every 8192` `--expert-profile-save` `--conversation-cache-mib 4096` **`--vision`（你确认要用，保留）** `--mtp-window 8192` `--vram-reserve-mib 832` `--ple-io mmap` |
| 3b | env 明细 | `HSA_OVERRIDE_GFX_VERSION` `STRATA_PREFILL_CPU_SHARE` `STRATA_PREFILL_CPU_SHARE_MAX` `STRATA_ROCBLAS_TUNING` `STRATA_GFX906_TUNED` `STRATA_CKPT_MOVE_PARK` `STRATA_DECODE_TIMING` `STRATA_SPEC_DEPTH` |
| 4 | 健康 | `/health` status=ok、`loaded:true`、**restarts=0**、StartedAt `2026-11-05T11:22:59Z` |
| 5 | 资源隔离 | `ulimit -l = unlimited`；引擎 `VmLck: 0 kB` / `Locked 0.00 GiB` |
| 6 | 显存布局 | `expert cache 7463 slots / 21.79 GiB`、`borrows 2606 (7.62 GiB)`、`882 MiB of VRAM free` |
| 7 | 回滚件 | 引擎 `strata-0.1.56-080`；`cp /data/strata-huihui-ud-iq4_xs.json.bak_w976 /data/strata-huihui-ud-iq4_xs.json` 后 `docker restart strata166-407` |
| 8 | 本轮改动 | 生产配置**净零改动**（chunk 32768 中性已回退）；账本 4 处；disk = build = running 三方一致 |

## 二、主线

`gfx906/mi50 @ 304bd3be` · tag `mi50-0.2.10-r32` · HEAD `33bddcfd` · 跟踪 `origin/gfx906/mi50` · **落后 0 / 领先 14** · 上游 `ffa80d73` · 工作树**脏 0 行**。

## 三、本次落生产

改动 **0**；**重启 2 次**（chunk 32768 臂 + 自动回退），各 ≈45 s，**停机合计 ≈1.5 分钟**；回滚件同上。`--vision` 保持开启。

## 四、进度 + 队列

**186 条 / 已结 112 / 60.2%**；主线 **158 / 112**；死块池 **0/28**。
队列：**R88 → R94 → R89 → P239 → P244 → P48 → P33 → R91 → R86 → R87**。

---

## 五、问题一：n-gram 现在起作用吗？在硬盘还是内存？

**起作用，而且在 token 路径上。** 证据链：

| 证据 | 内容 |
|---|---|
| 启动 | `PLE on, table 320001536 rows of …00002-of-00004.gguf` |
| 调用点 | `verify.cpp:3287` `ngram_rows(&tokens[t], prev, 1, ss.ple.consts, ple_rows…)` → `prefetch_rows()` → `gather_batch()`：**每个 verify 窗口按 token 取行** |
| 实测驻留 | 请求前 gguf 映射 `Rss 0.07 GiB` → 请求后 **0.36 GiB**，说明页在被真实触碰 |

**在内存还是硬盘：在内存的 page cache 里，按需分页、未锁定。**

| 模式 | 26.8 GiB 表的位置 | 进程 Rss | Locked |
|---|---|---:|---:|
| 改之前的 `--ple-io ram` | **全量 mlock 在 RAM** | ~103 GiB | **26.82 GiB** |
| 现在 `--ple-io mmap` | **page cache，按需**；只有被读过的行常驻（当前 ≈0.36 GiB） | **73.26 GiB** | **0** |

落盘永远在 NVMe（shard-2）。也就是说：**模型仍然“用”这张 26.8 GiB 的表，但不再把它整体钉在内存**——省下的 26.8 GiB 是“未触碰的页”，需要时从 NVMe（2.4 GB/s、4K 随机 16 µs）补，实测性能无差（W976：decode 39.7 vs 39.5、prefill 545/548 vs 508/551）。

## 六、问题二：你重开的移植/源码事项，我关了哪些？

**移植类一个都没关，全部 OPEN**：

| 条目 | 状态 | 内容 |
|---|---|---|
| R86 | **OPEN** | Q5_1 down 权重布局重排（43/48 层、88.6% 专家字节） |
| R87 | **OPEN** | q8_1 激活复用（外证 +2.2~2.6%，bit-exact） |
| R89 | **OPEN** | QSA prompt attention 只读选中 key（外证 +85%） |
| R91 | **OPEN** | dot8 生产接入六阶段（P1–P6） |
| R46 / R49 / R50 | **OPEN** | prompt attention 效率 / dense MMVQ 流水 / router BF16 GEMV |

**但你说得对，我确实关早了两处，已纠正**：

| 项 | 我当时怎么关的 | 纠正 |
|---|---|---|
| **R93（chunk 重标）** | 只测了 `8192 vs 16384` 就判 DONE | 今天补测 **32768**，三值齐了才算结案（见下） |
| **R90（上游基线升级）** | 判 DONE，但**验收里的质量门 KL/top-1 从未跑** | 降为 **PARTIAL**，新立 **R94**（质量门，OPEN） |

R84 是从 `INFLIGHT` 改 `BLOCKED`（不是关，是降级），解除条件写的是“dot8 微基准出数”。

## 七、R93 三值表（现在才叫测完）

| chunk | 2K | 8K | 16K | 判定 |
|---|---:|---:|---:|---|
| **16384（现役）** | 511.73 | 704.32 | **774.74** | 基线 |
| 8192 | 511.96（+0.04%） | 705.73（+0.20%） | **730.20（−5.75%）** | 判否 |
| 32768 | 507.82（−0.76%） | 705.16（+0.12%） | 777.12（+0.31%，band 0.32%） | 不显著 |

（每长度 n=3，CV 0.02–1.0%；两个臂都由门自动回退。）

## 八、方案进度与下一步

| 序 | 项 | 状态 |
|---|---|---|
| 1 | R93 chunk 重标 | **已完成（三值齐）** |
| 2 | R94 质量门（KL/top-1） | **新立 OPEN** —— R90 结案的欠账 |
| 3 | **R88 首块重叠** | 下一步：先加 prefill 分段计时（只加输出） |
| 4 | R89 / P239 / P244 / P48 / P33 / R91 | 排队 |

**下一步我直接做 R88-1**：在 prompt 路径打 CPU/GPU 分段计时，拿到首块 1.3 s 的分解；再据此决定预取实现（对齐 llama.cpp #28414「提前一个 split」与社区 fork「第二流预取 +64%」）。

`--vision` 按你说的**保留**，已写进参数册 P99 备注。
