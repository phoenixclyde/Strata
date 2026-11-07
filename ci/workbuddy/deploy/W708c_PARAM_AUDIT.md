# W708c -- 166 Strata 参数面审计：现状 / 未配候选 / 不该动

> 时刻：2026-10-08 00:40 CST ｜ 样本 = 容器 `strata166-402`（strata-gfx906:0.1.40.2，运行中）
> 判据来源：源码 `getenv("STRATA_*")` 全扫（310 个源文件）+ 引擎 `--help` 全文 + `docs/AMD_HIP.md` / `docs/DETAILS.md`

## 0. 结论

**不是最优，仍有"该配没配"。** 现在这 12 个参数是"能跑 + 无坑"的稳健档，
但至少有 **4 项有明确收益且未启用**；另有 **1 项容易误配**（`--expert-cache-per-layer`），必须说清。

开关总量：源码里 `STRATA_*` 环境开关 **280 个**；`AMD_HIP.md` 出现 **28 个**；`DETAILS.md` **47 个**；
`--help` 的 CLI 开关本次取全（落 `logs/_help_402.txt`）。绝大多数（多卡 / NVIDIA / Intel Arc / Windows / 调试）与本机无关。

## 1. 现已配置（12 项 + 3 项自动生效）

| 项 | 当前值 | 实测生效（当前启动块原文） | 评价 |
|---|---|---|---|
| `--pack` / `--native` | `/data/packs/ud-iq4_xs` / `...-00001-of-00003.gguf` | 301 native projection matrices, 2975 MiB | ✓ |
| `--mtp /data/mtp/rt` | ✓ | draft layer 1098 MiB VRAM；draft head 106299 tokens | ✓ |
| `--max-context` | `262144` | 模型原生上限 | ✓ |
| `--kv` | `k8v4` | 816 B/cell（int8 是 1056），K 保持 int8 精确 | ✓ 当前最优档 |
| `--spec 4` / `--spec-min-p 0.5` | ✓ | MTP 接受 61~69% | ✓（但见 §2.3） |
| `--expert-cache` | `auto` -> **9758 槽 / 21.98 GiB** | 策略 = **PROFILE, ranked by routing frequency, no eviction** | ✓ |
| `--expert-profile` | `/src/data/expert-profile.bin` | 24576 ranked pairs；8.2 s 填满 9758/9758 | ✓ |
| `--resident-budget-gib` | `76` -> **resident RAM mode** | RAM 33.45 GiB **page-locked**；`9758 + 14818 = 24576`；"**no file reads**" | ✓ 全部专家常驻 |
| `--prefill` | `auto` -> **chunk 8192 / 96-slot ring** | prompt path 借 1554 槽（3.49 GiB） | ✓ 但见 §2.2 |
| `--ple-io` | 默认 `direct` | PLE 表 320001536 行 | ✓（技能 A/B：`ram` 变体 -45%） |
| （自动）PCIe 探测 | -- | `13.2 GB/s -> pcie_frac 0.36（默认 0.55）` | ✓ 已自动调优 |
| （自动）CPU 池 | -- | 21 workers + host thread 同 drain，22 线程 | ✓ |
| （自动）CUDA graph | -- | 1/2/3/4/6-token 窗口**全部捕获成功** | ✓ |

## 2. 未配候选（按"收益 x 可测性"排序）

| # | 项 | 现状 | 依据 | 预期 | 本机可测性 |
|---|---|---|---|---|---|
| **1** | **`--expert-profile-save P`**（并让 `--expert-profile` 也指向它） | **未配** | `--help` L261-264：--serve 下在 QUIT 与每 10 分钟保存"自适应层学到的东西"（VRAM 里的专家 + 启动以来的路由计数）；用 `--expert-profile` 从它起步 | 每次重启**从零学**的问题消失；冷启动后缓存命中更早达峰 | 高（看启动填充耗时与首轮命中） |
| **2** | **`--prefill auto:16384` / `auto:32768`**（或 `STRATA_PREFILL_AUTO_MAX`） | **未配**（auto 只给 8192） | `--help` L235-237 明写这两个扩展档 | 大 prompt 预填可能更快 | **高 ---- 预填臂内极差只有 1.4%** |
| **3** | **`--calibrate` 定 `--spec-min-p`** | **未配**（`0.5` 是 setup 写的默认值） | `--help` L219-220："setup writes 0.5; **`--calibrate` measures it on this PC**" | 直接改 MTP 接受率（= 解码吞吐） | 高（看接受率） |
| **4** | **`STRATA_PREFILL_CPU_SHARE=auto`** | **未配**（默认关） | 0.1.40.2 note：prompt chunk < 1024 时快 **19~35%**；**2K 及以上不变** | 聊天/工具调用的首字明显改善 | **高（短 prompt 直接测）** |
| 5 | `--prompt-cache-tail` | 未配（默认 off） | `--help` L207-208：单卡再补一个靠近 prompt 末尾的 checkpoint | 长上下文 TTFT | 高 |
| 6 | `pin=N` | 未配 | 0.1.40.2 note：长文档连问首答 48~149 s -> **0.35~0.55 s** | 视使用模式，**数量级** | 需按真实用法测 |
| 7 | `STRATA_GR_SPLIT=1`（**gfx906 专属 opt-in**） | 未配（默认关） | `docs/AMD_HIP.md:461`：K-split down，**~3% per verify window**；默认关因求和次序不同（破坏位一致） | 解码 ~3% | **低** ---- 落在解码极差 11.6~13% 之下，须多轮重复；且改数值 |
| 8 | `STRATA_SPEC_GUMBEL=1` | 未配（默认关） | 0.1.40.2 note：AMD 报告者实测 **+5.7~9%** 解码 | 解码 | 同 7（分辨力） |
| 9 | `--conversation-cache-mib` | 未配（默认 0 = off） | `--help` L188 | 多轮会话停放/复用 | 高 |
| 10 | `--kv-grow` | 未配 | `--help` L131-134 | 上下文增长时让出专家槽 | **低** ---- `k8v4` 下 KV 极小（816 B/cell x 262144 = 214 MiB） |

## 3. 明确**不该动**的（防误配）

| 项 | 为什么不动 |
|---|---|
| **`--expert-cache-per-layer`** | `--help` L288-293 说默认"按到达顺序从一个共享计数器分配"，256 槽散到 26 层的 position 0、实测 **2.97%**；per-layer 好得多（8 槽/层 21.4%、64 槽/层 70.4%）。**但我们的策略是 PROFILE 驱动**（日志明写 `PROFILE, ranked by routing frequency, no eviction`），且**实测解码缓存命中 94.6~96.4%** => 已远好于该文档数字，**不要改** |
| `--ple-io ram` / `mmap` | 技能 §7.7 实测：`ram` **-45%**、`mmap` 噪声级 |
| `--no-pool` | 会砍掉 CPU 专家池；我们是"CPU 参与计算"的形态（21 workers） |
| `STRATA_EXP_MODE=2` / `STRATA_MMVQ_WAVE=0` / `STRATA_ROUTE_PER_TOKEN=1` / `STRATA_GR_FAST=0` | 这些是"**恢复 CUDA 布局**"的反向开关；在 gfx906 上等于退化 |
| `--layer-split` / `--expert-cache-device1..3` / `--peer-device` / `--remote-expert-opt` | 单卡 |
| `--vram-elastic` | `--help` L193 明写 NVIDIA |
| `STRATA_HIP_WMMA` / `STRATA_HIPBLASLT_TUNING` | gfx906 无 WMMA、无 hipBLASLt（note 里那张表是 RX 7900 XTX） |
| `--batch` / `--slots` / `--batch-mtp` | 单用户不需要，且每槽吃 VRAM |
| `--adapt-async 1` | 非逐位一致，先不动 |
| Intel Arc / Windows / 诊断类（`--stage-timing` / `--stats` / `--dump-*`） | 与生产无关 |

## 4. 建议执行序（一次只动一个变量）

1. **批次 A（零风险）**：`--expert-profile-save` + `--prompt-cache-tail`；另跑一次 `--calibrate` 定 `--spec-min-p`。
2. **批次 B（短 prompt 首字）**：`STRATA_PREFILL_CPU_SHARE=auto`。
3. **批次 C（长预填）**：`--prefill auto:16384` / `auto:32768`。
4. **批次 D（解码，须多轮）**：`STRATA_GR_SPLIT=1`、`STRATA_SPEC_GUMBEL=1` ---- 每臂 >=5 轮 x 3 次才可判。
5. 若用法是"同一长文反复问"：上 `pin=N`。

**判定线（沿用 W708 方法学）**：同容器、同权重、**一次只改一个变量**；预热 1 条丢弃 + 重复 3 次取中位与极差。
**预填侧**差异 > 2% 才算有效（臂内极差 1.4%）；**解码侧**差异 < 11.6% 一律判"本机不可分辨"。

## 5. 产物

- 本件：`D:/strata166/W708c_PARAM_AUDIT.md`
- 原始素材：`D:/strata166/logs/_cfg_402.txt`（容器 env / 配置 JSON / **当前**启动块 / 完整 `--help` / docs 开关清单 / `/src/data` 可写性）
- 环境开关全表：`D:/workbuddy/_z_rk81/_strata_envs.json`（280 个，含 file:line）
