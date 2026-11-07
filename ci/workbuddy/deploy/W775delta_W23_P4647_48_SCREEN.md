# W775delta W23 ---- `P46` / `P47` / `P48` 承载与排序（源码级筛选，0 发车）

> 触发：`W750 §0.7` 完整性核查补登记的 `W23`（三条 CANDIDATE 有计数无承载）。
> 判据顺序（`W27` 立）：**(1) 读源码定机制 -> (2) 与本机形态逐条对照 -> (3) 吻合才设计车**。
> 本件 0 发车：全部结论来自 0.1.42 源码（`deploy/tmp/src142/`）+ 产线实读。

## 0 结论（先行）

1. **`P46`（io 预取族 4 键）：本机无 decode 杠杆** —— `FILL_AHEAD` 只在**启动 profile 填充**里起作用；`FS_AHEAD` 需 `STRATA_FS_SLOTS>0`（我们没设，未激活）；`FETCH_THREADS` 只服务**文件层读**；`IO_PREFETCH` 已 `P54 REJECTED`。
2. **`P47`（drafter 族 7 项）：只有 `--mtp-draft-vocab` 是真候选**；`--coupled-draft` 在 `temperature=0` 下恒空操作；`--no-spec-split` 就是引擎默认、`--spec-split` 上游实测**更慢**；`--spec-follow` / `--window-hashes` 是 bench/diag 口。
3. **`P48`（misc 族 6 项）：3 项 inert/N-A、3 项真候选** —— 真候选 = `--pcie-mode dma` · `STRATA_EMB_REUSE_ACCOUNT=1` · `STRATA_KV_GROW_HOLD=1`（最后一条**改答案风险**，须配质量门）。
4. **附**：`adapt()` 层参数扫描（零停机，复用 `W26` 工具链）=> **引擎默认即最优**（见 §4），与 `P27 REJECTED` 一致。

## 1 `P46` 逐条（源码行号）

| 键 | 源码 | 判定 |
|---|---|---|
| `STRATA_FILL_AHEAD`（默认 256） | `generate.cpp:5047-5055`：设置处带前置 `if (!per_layer && srcp == &src && !src.unbuffered())`，**在是 profile 填充循环内**（`:5056 fill_t0` / `:5058 for i in want`） | **启动期旋钮**（只改 profile 填充的 I/O 交叠，即那 ~8 s）=> **decode 面上 inert**，无速度价值 |
| `STRATA_FS_AHEAD`（默认 1） | `:5386-5387`：`fs_ahead = (STRATA_FS_SLOTS > 0) && (FS_AHEAD != 0)` | **本机未激活**（我们没设 `STRATA_FS_SLOTS`）。产出日志里那句 `routing-aware prefetch on (the next layer's router, file tier)` 来自**另一支**（文件层 `src.warms()` 的页温预取，由 `STRATA_LOOKAHEAD` / `_K` 控制，默认开） |
| `STRATA_FETCH_THREADS`（默认 8） | `:4522-4523` `src.set_fetch_threads()` | 只服务**文件层读**（上游 `UNSLOTH_Q4.md:235`：16 不比 8 快）=> 边际 |
| `STRATA_IO_PREFETCH` | `:4561` + `expert_source.hpp:700`（"the Linux I/O path of the mapped file tier"） | 已 `P54 REJECTED`（实测 `io prefetch: 0 read ahead`）=> 关闭 |

**产线定量旁证（现取）**：`resident RAM: 33.44 GiB of experts in RAM, **210,986** exchanged with the VRAM tier, **24,720** blob reads from the file`
=> 主的通道是 **RAM <-> VRAM 交换（21 万）**，文件读只有 **2.5 万**（8.5 倍差）=> 这一族（面向"文件层读"）**在本机形态下不是杠杆**。

## 2 `P47` 逐条

| 项 | 源码 | 判定 |
|---|---|---|
| `--coupled-draft`（= `STRATA_SPEC_COUPLED`） | `generate.cpp:1879` + `coupled_draft.hpp:75` + `DETAILS.md:1211`（*"With temperature above 0 the engine keeps a draft only when it equals the token the model sampled"*） | **我们 `temperature=0` => 恒空操作**（与 `P29 SPEC_GUMBEL` 同型） |
| `--lookup-chain-min M`（默认 3） | `:1995` `std::max(3, atoi(...))`，且需 `--lookup-chain` 先开 | 从属 **`P42`**（`--lookup-chain`）=> **须与 P42 串行**，不单独发车 |
| `--mtp-draft-vocab FILE` | `:2011` + `mtp.hpp:65`（默认 `<mtp>/draft_vocab.bin`） | **真候选**：草稿头的 token 子集。上游带 `tools/draft_vocab.py` 可造 => 本卡**接受长度只 1.797（W740）**，是 decode 轴上少见的直接杠杆 |
| `--no-spec-split` / `--spec-split` | `:2044`；`A770_SPEED_SPEC.md:254-257` 逐字 *"`--spec-split` **HURTS** — 9.9/10.2/10.3 vs `--no-spec-split` 11.7/12.1/12.6 ... The engine default matches `--no-spec-split`; keep it"* | **惰性**（默认即 `no-spec-split`）+ **已知更慢**（另一支）=> 不发车 |
| `--spec-follow PATH` | `:832` *"benchmarks: emit this continuation (token ids) instead of the argmax"* | **bench 口**，非性能旋钮 |
| `--window-hashes PATH` | `:835` "per verify window, a line with its index, position, size, a 64-bit hash of ..." | **诊断口** |

## 3 `P48` 逐条

| 项 | 源码 | 判定 |
|---|---|---|
| `STRATA_EXPERT_V2K` | `iq_kernels.cu:2349`（`s26_gu_l_kernel` 结构，K-quant 专用流） | **对本 pack 不适用**（我们零 K-quant，`W738`） |
| `STRATA_GFX1151_DEFAULTS=0` | `arch_defaults.cpp:33` + `arch_defaults.hpp:10`（*"turns the whole table off"*） | **本卡 inert**：gfx906 的 `arch_default_env()` 返回**空表**（`arch_defaults.cpp:32`）=> **没有东西可关** |
| `STRATA_PF_SWITCH_MIN_T` | `qsa_prompt_attn.cu:1432`；上游 `STRIX_HALO.md:124` 逐字 *"gates **only** the hyper-connection and padding switches"*（即 `PF_FUSED`/`PF_GEMM`/`PF_PAD`） | **inert**：我们没启用那些（且它们属"改答案"权威名单） |
| `--pcie-mode` | `generate.cpp:1961` + `docs/BATCHED_DMA.md`（`--pcie-mode dma` + `STRATA_DMA_BATCH=1` 提交一个 verifier group 的独立 DMA） | **真候选**：我们 PCIe 路径活跃（`--pcie-frac 0.20`）=> 单键先测 `--pcie-mode dma`（`DMA_BATCH` 是其子旗，**不同车**） |
| `STRATA_EMB_REUSE_ACCOUNT=1` | `prefill.cpp:260-263` 逐字 *"lets it use the saved bytes: **a larger chunk or more borrowed slots where VRAM is the limit**"* | **真候选**：我们**正是 VRAM 受限**（`vram_free_mib: 574`）=> prompt 侧杠杆（prefill 口径） |
| `STRATA_KV_GROW_HOLD=1` | `generate.cpp:10167-10168` *"keep the K/V as long as the longest parked conversation; default: trim to this request alone"* | **真候选但风险**：改 KV 驻留 => 改专家槽 => **可能改答案**（须配 `STRATA_LOGPOS` 质量门）；且与 elastic KV 交互（`P63` 族） |

## 4 附：`adapt()` 层参数扫描（零停机，`W26` 同工具链）

同一 trace / 同 profile / 9,761 槽：

| 配置 | share | swaps |
|---|---|---|
| `--swaps 8` | 0.9139 | 1,920 |
| `--swaps 32` | 0.9483 | 7,041 |
| **默认（every 4 / swaps 96 / decay 0.70 / margin 1.5）** | **0.9564** | 11,601 |
| `--every 8` | 0.9515 | 10,084 |
| `--every 16` | 0.9417 | 5,760 |
| `--decay 0.50` | 0.9555 | 10,946 |
| `--decay 0.90` | 0.9581 | 13,493 |
| `--margin 2.5` | 0.9531 | 7,814 |

=> **默认即最优**（最好的替代 `--decay 0.90` 仅 +0.17pp，代价 +16% 交换，在噪声内）。与 `P27`（`--adapt-every/--adapt-swaps/--adapt-decay`）**已 REJECTED** 一致。

## 5 自查：我差点误报"三个从未登记的旋钮"

初判时我以为 `--pool-workers`（产线跑 **21**，上游 A770 文档说 6/7 wash、最优配置用 7）、`--adapt-*`、`STRATA_LOOKAHEAD*` 是**未登记面**。**回 register 逐条核后否决**：
- `--pool-workers` => **`P26` REJECTED**
- `--adapt-every/--adapt-swaps/--adapt-decay` => **`P27` REJECTED**
- `STRATA_LOOKAHEAD_STATS` / `tools/replay_cache_policy.py` => **`P58` REFERENCE**（rel0142 台账 O-13）

=> 教训：**"我印象里没登记"不等于"未登记"**；提"缺口"前必须先 grep register。

## 6 待裁定（改 status 属签字项，本件未动 register status）

| ID | 现值 | 建议 |
|---|---|---|
| `P46` | CANDIDATE | 建议 **REJECTED**（族内 4 键本机均无 decode 杠杆；理由见 §1） |
| `P47` | CANDIDATE | 建议**收窄**为单条 `--mtp-draft-vocab`（其余 6 项 inert/默认/负） |
| `P48` | CANDIDATE | 建议**拆条**：保留 3 真候选（`--pcie-mode dma` / `EMB_REUSE_ACCOUNT` / `KV_GROW_HOLD`），其余 3 项标 N-A/inert |

## 7 复现

```
# 源码（本地归档 0.1.42）
sed -n '5047,5055p' src/program/generate.cpp      # FILL_AHEAD（profile 填充内）
sed -n '5386,5387p' src/program/generate.cpp      # FS_AHEAD（需 FS_SLOTS>0）
sed -n '10167,10168p' src/program/generate.cpp    # KV_GROW_HOLD
# 产线数（只读）
grep -a 'resident RAM:' <prod log> | tail -6
# adapt 扫描
python tools/replay_cache_policy.py <trace> <expert-profile.bin> 9761 --swaps 32
```
