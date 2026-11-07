# W775delta ---- 「本机不采用，但对外有价值」清单（EXT）

日期 2026-10-11 13:06 ｜ 工作区 `D:/workbuddy_space/strata_ws/` ｜ 触发：机主「**我们不用不见得别人不用**」

> **[W20 复核 2026-10-11 19:5x]** 触发条件（改驻留模式）**已于 17:37 兑现** => 13 行逐项复核完毕：**仅 `P54` 一行需重述**（其理由引用了已废的 `--resident-budget-gib 76`）；**其余 12 行的理由均不挂在 `--resident-*` 上**；**新增 `P09` 一项 EXT**。详见 `deploy/W775delta_W20_EXT_RECHECK.md`。

> **本文回答的是"哪些是我们自己用不上/够不着，但别人用得上"** ---- 与 `W775delta_W17_SWITCH_LANDSCAPE.md`（本卡可达性清点）互补。

**本件的待办状态（防丢，2026-10-11 13:1x 补）**

- **已登记为 `W750_MASTER_PLAN.md` 的 `W20`**（三处齐：§0.6 表 · §1 行动项表 · §2 第 23 项）；规则本体在 §0.5.6。
- **已执行**：§4 的四条建议 **已发上游 = issue [`#1926`](https://github.com/Niko1221/Strata/issues/1926)**（POST 201 + 回读逐字节一致）。
- **复核触发条件**（任一发生就重跑本文）：换 `--kv` · 上多卡 · **改驻留模式 `--resident-*`** · 换 pack · 启用 PLE 表 ----
  **[!] 2026-10-11 17:37 已兑现**：驻留模式由 `--resident-budget-gib 76` 改为 `--resident-experts` + `STRATA_RESIDENT_HEADROOM_GIB=0.5`（`P09` 废、`P66`/`P65` 采纳）=> 本表逐项复核见 `W775delta_W4X_RES_RESULT.md` §8-§11。
  因为每条 EXT 的"本机为何不用"都挂在这些配置上。
- **纪律**：新裁定一律带 `[EXT: <适用面>]` 标签（由 W752 的全库 grep 同步带出；不加 status/列数，`gen_config`/`verify_config` 不受影响）。

## 0 规则修正（本次立）

**旧写法的问题**：把"我们不用"直接写成「不适用 / REJECTED」，下一个读者会读成"机制上不行"，于是**既丢掉对外价值、也丢掉推上游的素材**（`Q8_PACKED` 就是这么被写窄的）。

**新规则（四车道 + 标签）**：每条"不采用/不适用"的裁定必须分流四问：

| # | 车道 | 必答 |
|---|---|---|
| 1 | **编译期可达？**（本卡二进制是否含该字面量） | 是 / 否（否 => 死在 `#if`） |
| 2 | **运行期可达？**（**本机配置**下能否拨到） | 是 / 否（否 => 写明**被什么挡住**） |
| 3 | **本机是否采用？** | 采用 / 不采用（不采用要写**为什么**） |
| 4 | **对外是否有价值？** | **有 => 必须加标签 `[EXT: <适用面>]`** |

**硬约束**：只要第 2 问在**别的配置或硬件**上答案为"是"，**禁止只写"不适用"**，必须带 `[EXT: ...]`。
**标签取值（可 grep）**：`[EXT: --kv int8]` · `[EXT: 非 native pack]` · `[EXT: 启用 PLE 表]` · `[EXT: 多卡]` · `[EXT: 大显存/RAM 宽裕]` · `[EXT: 小 RAM 预算]` · `[EXT: CUDA 用户]` · `[EXT: Windows 用户]` · `[EXT: wave32 卡]` · `[EXT: temperature>0]` · `[EXT: 上游防重复]`。

## 1 已识别的 EXT 行（本机不采用/够不着，别人可用）

| ID | 标的 | 本机为何不用 | **对外适用面** | 标签 |
|---|---|---|---|---|
| **P55** | STRATA_GFX906_ATTN_QUERY_SWIZZLE | k8v4 => 主模型 `kv_mode=3`，路径恒假 | `--kv int8` 用户可达（`active=1 kv_mode=1` 已实证）；上游逐字说 **k8v4 的 MTP drafter 也走该路径** | `[EXT: --kv int8]` |
| **P56** | STRATA_GFX906_ATTN_REDUCE12 | 依赖 P55，同被 k8v4 挡住 | 同 P55（`--kv int8` 用户） | `[EXT: --kv int8]` |
| **P52** | `--dump-logits` / `--logits-stride` | 我们走 **native pack**，逐位置循环永不执行 | **非 native pack 用户可用**（上游 `bench/results/2026-09-27-esp/` 就用了它）；也是"全词表 logits 出口"这条更强的门 | `[EXT: 非 native pack]` |
| **P58** | `STRATA_PLE_PROBE` / `--ple-io` 相关 | **[更正 2026-10-14]** 生产 args 未给 `--ple-*`，但引擎**自动加载了 PLE 表**（`PLE on, table 320001536 rows` 38 次）；缺省 `direct` 被探针在 **14,560 / 13,268 rows/s** 下**自动切成 `mmap`**，即**本机正是该情形的实际使用者** | **启用 PLE / n-gram 表的用户**：该探针会把 `--ple-io direct` 自动切 `mmap`（低吞吐盘上的行为变化） | `[EXT: 启用 PLE 表]` |
| **P54** | STRATA_IO_PREFETCH | **[W20 重述 2026-10-11 19:5x]** 本机 128 GiB RAM；现行驻留模式 = **`--resident-experts`（无 RAM 预算）+ `STRATA_RESIDENT_HEADROOM_GIB=0.5`**（`--resident-budget-gib 76` **已废**，`P09` -> REJECTED）=> 补集 **36.93 GiB**（含借区 1,554 槽 / 3.49 GiB），且 **B7 固化后稳态 `0 blob reads`、`file tier ... for 0.0 MB of expert reads`** => 预取对象**比 W773 实测（≈0）更少** | **`--resident-budget-gib` 调小、或 pack 大到专家装不进 RAM 的机器**：file-tier I/O 成主路径，本条就有用（register 逐字 limitation） | `[EXT: 小 RAM 预算]` |
| **`P09`** | `--resident-budget-gib` | **[W20 新增 2026-10-11 19:5x]** **本机已废**：`budget_bytes > 0` => 设计性关闭借区（`expert_source.hpp:550-552` 逐字 "No lend region then"），prompt 借走的槽每 chunk 从模型文件补回；B7 换掉它后冷 `read_ms` **-2.50%**（区间不重叠） | **RAM 预算紧张、必须给引擎设内存上限的机器**：这是**唯一**能在启动期把页锁定补集压下来的旋钮（`expert_source.cpp:2649-2650` `budget = available - headroom`）；我们敢不用它是因为 RAM 宽裕（128 GiB） | `[EXT: 小 RAM 预算]` |
| **P53** | `--layer-split` / `STRATA_USE_HIP` 编译宏面 | 本机单卡；宏面为编译期 | **多卡用户**（层切分）；`STRATA_USE_HIP` 面与"哪些块被编进二进制"直接相关 | `[EXT: 多卡]` |
| **P57** | v0.1.42 非 gfx906 新开关族 | 多卡/Intel/gfx12/Windows 是我们没有的硬件；改答案类触本项目一票否决 | **多卡 / Windows / Intel / gfx12 用户**；其中 `ROUTE_TAIL_SKIP` 已证**在我方是活的**（见 §2） | `[EXT: 多卡]` |
| **P29** | STRATA_SPEC_GUMBEL | 我们默认**贪心解码** => 恒空操作（上游逐字：非结构性缺陷） | **任何 `temperature > 0` 的采样用法**：设 `=1` 即可，无需引擎改动 | `[EXT: temperature>0]` |
| **P36** | STRATA_EXPERT_V2 | gfx906 实测 **-5.60%** | 上游防重复劳动（该值取自 gfx1151，我们在 gfx906 复现为负） | `[EXT: 上游防重复]` |
| **P37** | STRATA_TSUM | gfx906 上**不可复现**（中性） | 同上（本卡唯一数据点） | `[EXT: 上游防重复]` |
| **P40** | STRATA_SH_STREAM | 本 pack 实测 **-0.13%**（上游对 UD-Q4_K_XL 是 +1.8%/+6.7%） | 上游防重复；**其它 pack 用户**可能仍获益 | `[EXT: 上游防重复]` |
| **P45** | 非专家张量精度路线（routeK T1） | gfx906 实读：lm_head/qkv/shexp **已是 Q8_0** => T1 前提不成立 | 上游防重复；**其它 pack（真有 BF16 非专家张量）的用户**仍成立 | `[EXT: 上游防重复]` |

## 2 本卡**可达但本机不采用**（`[GFX906-OK]`，与新规则第 1/2 问的区别）

| 标的 | 可达性证据 | 本机为何不用 | 对外适用面 |
|---|---|---|---|
| `STRATA_Q8_PACKED` | 二进制含字面量 + DT 实证 `packed 84 Q8_0 matrices for decode`；**须显式设**（gfx906 取空表） | 本机实测 **无增益**（+1.57%/+2.78% 均 < 臂内 spread）且 **+1.87 GiB VRAM** | **该表默认生效的卡（gfx1151 / gfx12-prompt 半边）**；上游另需知道"gfx906 不兑现" |
| `STRATA_Q6_PACKED` | 同上（同一 patch 族） | 同上 | 同上 |

> **重要事实（据实纠正）**：`Q8_PACKED` / `Q6_PACKED` 都是**无损重排**（`native_mmvq.hpp:96` 逐字 *"a **lossless** load-time repack"*；`:106` *"the **same bytes** as ql / qh"*）=> **不改精度、只买速度**。所以"精度会提升"这个前提**不成立**；它们在**本卡**是"零速度收益 + 1.87 GiB 代价"。

## 3 架构面：本卡**编译期排除**，别人有（W17 的 34 条里**守卫可判的 19 条**；余 15 条见节末）

| 守卫 | 数量 | 谁可用 |
|---|---:|---|
| `#if !defined(__HIPCC__)`（含宏间接） | 8 | **CUDA 用户**（`BF16_TC` / `GDN_KEYHEAD` / `GDN_CHUNKED` / `MMVQ_IL_ROWS` / `QSA_CLUSTER` / `SM70_TABLE` / `TOPK_STREAM` / `ATTN_PRE75`） |
| `#if defined(_WIN32)` / `#ifdef _WIN32` | 5 | **Windows 用户**（`DEFERRED_REGISTER` / `FETCH_PVM` / `FILE_RELEASE` / `STARTUP_UNBUFFERED` / `WDDM_BUDGET`） |
| `#if defined(STRATA_WMMA_GFX11)` / `hipBLASLt` / `PREFILL_MMQ` / `EXP_LAYOUTS` | 4 | **gfx11 / gfx1151 / 特殊构建** |
| `#if defined(__linux__) && !defined(STRATA_HIP_GFX906)` / `!USE_HIP && !GFX906` | 2 | **非 gfx906 的 AMD / CUDA-SYCL**（`UMA_HEADROOM_GIB` / `MTP_PRIORITY`） |

**未分类的 15 条**（守卫链为 `#else` / 间接宏 / 未判 => **不在本表内**，逐条见 W17 §3）：
`DF_PDL` · `HIP_ROUTER_OLD` · `QSA_WARP` · `SELECT_SIMT` · `MULTI_BLOCK_ARGMAX` · `TOPK_ACTIVE_ANY` · `TOPK_CAPACITY_GUARD` · `SESSION_GOLDEN_PRINT` · `PF_FUSED_TILE` · `HIP_ADAPT_KERNEL_COPY` · `KV_HOST_DMA` · `WMMA_BF16` · `WMMA_GEMM` · `PLE_GGUF` · `ATTN_PRE75`

> 更正（2026-10-11 审计 #3）：本节标题原写「W17 的 34 条再分类」，**实际只覆盖 19 条** => 已改正。

## 4 建议推上游的内容（**草稿，未发**）

1. **gfx906 实测修正表**：`arch_defaults.cpp` 该表的 **decode 半边**（`Q8_PACKED` +2.3% / `EF` 等）在 MI50 上**不兑现**；而 gfx12 侧上游自己已写 *"the decode half measured slower on that card, so it stays out"* => **建议把"decode 半边=非 gfx1151 专属"写成表注释/文档**，免得 MI50/其它卡用户照抄。
2. **`P54` 的可用面**：`IO_PREFETCH` 的收益前提是"专家不完全驻留"；我们实测预取 **0 次**（RAM 128 GiB + page cache 78 GB）；建议在 release note 里写清"**大 RAM 主机上本条是空操作**"。
3. **`ROUTE_TAIL_SKIP` 的 AMD 描述**：relnotes 逐字 *"off ... on AMD and Intel"*，但**我方 gfx906 实测 ON(default) 且在动作**（12/12 次启动、`route tail skip: N missed experts skipped`，N 达 672,855）=> 建议上游复核该句与"CUDA-分支编译"的关系。
4. **`P52` 的 native pack 限制**：`--dump-logits` 在 native pack 下永不执行，建议写进 `--dump-logits` 的 help。

## 5 局限

1. 第 1 节的"对外适用面"是**源码/文档级推断**（未在那些配置上实测）；只有"本机为何不用"是实测。
2. 第 3 节的守卫分类基于 `strings` 命中 + `#if` 栈（见 W17 件 §1）；宏间接处已人工核过 12 条样本。
3. `[EXT]` 标签**不动 status、不动列数** => `gen_config.py`（只吃 ADOPTED）与 `verify_config.py` 均不受影响。
