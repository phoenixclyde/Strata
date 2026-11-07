# W775delta W25 #11 ---- 吸收上游 gfx906 社区报告（只读）

日期 2026-10-11 ｜ 源 = 上游 `Niko1221/Strata` 的 `bench/results/`（API 现取）｜ 零发车

## 0 目的与判据

`W713 §6.4 #11` 原话：把其余 gfx906 报告逐份读、与我们 register 的 P 编号逐条对齐，
看有无**我们未登记而别人已实测**的结论（避免重复劳动 / 漏项）。

## 1 清点：gfx906 相关报告共 5 个目录（`bench/results/` 共 131 个）

| 目录 | 卡 | 状态 |
|---|---|---|
| `2026-10-03-community-2x-mi50` | 2x MI50 16GB | **本件新读** |
| `2026-10-04-community-mi50` | MI50 32GB | **本件新读** |
| `2026-10-09-community-radeon-pro-vii-16gb` | Pro VII 16GB | **本件新读** |
| `2026-10-08-gfx906-qsa-query-swizzle` | 2x Pro VII | 已读（`W713 §6.4 #9`） |
| `2026-10-04-community-4090-32gb-ram-512k` | RTX 4090 | 非 gfx906，不计 |

## 2 三份报告摘要（逐字取自上游 README）

| 项 | 2x-mi50 | mi50 32GB | radeon-pro-vii 16GB |
|---|---|---|---|
| 引擎 | 0.1.38 | 0.1.38 | 0.1.40.4 与 0.1.41 |
| pack | Coder IQ1_M | 原版 IQ2_XS | 原版 IQ2_XS |
| 上下文 | 131,072 | 131,072 | 131,072 |
| KV | `--kv int8 --kv-resident 32768` | 同左 | 同左（照搬） |
| 专家槽 | 6,912+5,376 = all 12,288 in VRAM | **19,304**（hit_rate 0.97-0.995） | 同左 |
| prefill | `--prefill 4096` | `--prefill 2048` | `--prefill 2048` |
| MTP | `--spec 4 --spec-min-p 0.5` | `--spec 3 --spec-min-p 0.9` | `--spec 3 --spec-min-p 0.9` |
| 其它 | `layer_split 27` · `--vram-reserve-mib 600` · `--pcie-frac 0` · **`STRATA_ARENA_MMAP=1`** | `--vram-reserve-mib`（默认） | + `--vram-reserve-mib 1024` |
| vision | 无 | 无（mmproj 未传） | 无 |
| decode tok/s 4K/32K/128K | 50.1 / 47.8 / 45.7 | 36.0 / 34.0 / 33.5 | 24.2 / 24.0 / 23.7 |
| prompt tok/s | 321 / 523 / 517 | 331.9 / 327.2 / 305.2 | 350 / 339 / 284 |

> **口径警告（必须随行）**：三者引擎（0.1.38 / 0.1.40.4 / 0.1.41）与 pack 都与我们（**0.1.42 + UD-IQ4_XS**）不同，
> 且**专家总数不同**（原版 IQ2_XS = 12,288；我们的 UD-IQ4_XS = 24,576）=> **decode tok/s 不可直接与我们比**。

## 3 产出：3 项**我们从未登记**、而社区已在 gfx906 上实测的开关

| # | 开关 | 上游用法 | 我们的 register | W17a 判定 |
|---|---|---|---|---|
| 1 | **`STRATA_ARENA_MMAP=1`**（#640） | 2x-mi50 报告逐字：*the expert arena as a read-only mapped file; 23.4 GiB of VRAM-held experts handed back to the OS at start*；**要求 `--pcie-frac 0`** | **无行**（全库 grep = 0） | M 桶，门 = **本卡专属（开）**，守卫逐字 `#if (defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)) && !defined(_WIN32)` |
| 2 | **`--vram-reserve-mib`** | 三份报告全用（600 / 默认 / 1024） | **无行** | CLI 面（非 env） |
| 3 | **`--kv-resident`** | 两份 131K 报告都用 `--kv-resident 32768`（每层 32768 KV cell 驻 VRAM，其余从 RAM 流式） | **无行**（仅在 P03/P04/P32/P43 的 requires/conflicts 列被提到） | CLI 面（非 env） |

### 3.1 为什么这三条值得登记（不是别人用我们就用）

- **`STRATA_ARENA_MMAP`**：**机制上就是本卡专属**（守卫含 `defined(STRATA_HIP_GFX906)`），作用是把
  **VRAM 里持有的专家交还给 OS** ---- 我们有 33.44 GiB 专家常驻 VRAM（总量 34.34 GB），**VRAM 正是瓶颈**
  （P07 实取 9,761 槽 / 21.98 GiB）。这条**直接对口槽位天花板**，而我们从没登记过。
- **`--kv-resident`**：社区正是靠它把 131K 上下文塞进卡里（KV 流式，不全驻 VRAM）。我们跑 **262,144** 上下文
  且没有用它 ---- 这是 KV 面省 VRAM 的现成手段，与 `P32`（`--kv-grow`，已 REJECTED）不是同一机制。
- **`--vram-reserve-mib`**：与我们已登记的 `--resident-budget-gib 76`（**RAM 侧**）是两个不同的预算面。

### 3.2 顺带一条参数档位差异（不需新开关）

社区 `--spec-min-p` 用 0.5（2x-mi50）/ 0.9（mi50、pro-vii）；我们 `P06` 实测最优是 **0.70**（calibrate 扫过 0.3/0.5/0.7）。
=> **不构成行动项**（我们已在本卡扫过、0.70 最优），仅记录存在分歧。

## 4 落地

- 新增 register 行 `P61` / `P62` / `P63`（`CANDIDATE`，未测；`gen_config` 只吃 `ADOPTED` => 配置面不变）
- 新增行动项 `W27`，挂 `W17b` 的 KV/IO 族之后
- `W713 §6.4 #11` 标记完成

## 5 局限（必须随行）

1. 三份报告都是别人的机器（不同 CPU / ROCm / 内核 / 隔离度），不是可控对照。
2. 版本跨 0.1.38-0.1.41 与我们 0.1.42 不同；跨版本只比形状，不比绝对值。
3. 本件只做**登记与对齐**，**没有任何本机实测**；三开关是否在我们这兑现，须各自发车。

## 6 产物

- `deploy/tmp/_up_gfx906_reports.txt`（三份 README 原文抽取，21,289 B）
- 抓取脚本 `deploy/tmp/_up_reports.py` / `_up_check.py`
