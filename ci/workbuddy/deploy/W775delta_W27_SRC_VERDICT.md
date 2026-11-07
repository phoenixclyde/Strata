# W775delta W27 ---- 社区三开关的**源码级判定：本机不发车**（据实否掉）

日期 2026-10-11 ｜ 源 = 本机 0.1.42 源码树 `deploy/tmp/src142/` ｜ **0 发车**

## 0 为什么先读源码再决定

`W27` 是机主「我们不用不见得别人不用」那条线派生出来的：三开关由 **gfx906 社区报告**（2026-10-03 2x-MI50 16GB / 2026-10-04 MI50 32GB / 2026-10-09 Pro VII 16GB）实测过，我们从未登记。
**但"别人用了"不等于"我们该用"** ---- 故本件先读源码定**机制**，再决定是否花一次车。

## 1 逐条判定

### 1.1 `STRATA_ARENA_MMAP=1`（#640）---- **机制与本机相反，不发车**

`docs/DETAILS.md:199` 逐字：

> **A mapped arena for small RAM (Linux, opt-in, 0.1.39, PR #640):** `STRATA_ARENA_MMAP=1` maps a native pack's expert arena read-only from the pack's `experts.bin` **instead of reading it into locked RAM, for a PC whose GPUs hold most experts but whose RAM is small** (2x 16 GB GPUs with 32 GB of RAM: ~1 GB -> 25 GB available while serving). ... **The pages of the experts a GPU holds are handed back to the OS.** **Run it with `--pcie-frac 0`** (the GPUs get no mapped alias). Without the variable nothing changes.

| 判据 | 上游目标场景 | 本机实况 | 是否吻合 |
|---|---|---|---|
| RAM 大小 | **小**（32 GB） | **128 GiB**（日志：33.44 GiB 专家 page-locked，另 84.0 GiB 可用） | **否** |
| 专家谁持有 | **GPU 持有绝大多数** | **RAM 持有全部 24,576；GPU cache 仅 9,761（40%）** | **否** |
| 该开关效果 | 把 GPU 持有的专家页**交还 OS** | 会**削减**我们本已紧张的 GPU cache | **反向** |
| 配套要求 | `--pcie-frac 0` | `P25` calibrate 实测 0.20=35.68 > 0.00=35.19（0.20 更快） | **反向** |

**=> 四个判据全部不吻合，其中两条方向相反。不发车。**

### 1.2 `--vram-reserve-mib` ---- **边际，不发车**

`docs/AMD_HIP.md:199` 逐字：**"keep more VRAM free than the default 700 MiB"**（场景是**显卡还要驱动 Linux 桌面**，不这么做会被 `systemd-oomd` 杀进程）。
本机：**无头专卡**（生产日志：`574 MiB of VRAM free with everything loaded`）。调高 = 减少可用 cache 槽；调低 = 冒缓冲分配失败风险。在 9,761 槽的量级上，几百 MiB 对应的是**几十槽**。
**=> 机制面向的是"共享桌面的卡"，与我们的专卡形态不符。不发车。**

### 1.3 `--kv-resident N` ---- **边际，不发车**

语义（`DETAILS.md:94`）：每层 N 个 KV cell 驻 VRAM、**其余从 RAM 流式**。
本机：已在 `--kv k8v4` + `--max-context 262144` 下**整段驻留**运行，且命中率 95%+（见 `W775delta_W13_HEADROOM_RECHECK.md`）。
改成流式 = **拿 PCIe 流量换 VRAM 槽位**；而 `P54`（IO_PREFETCH）已证我们 file/RAM tier 非瓶颈。
**=> 收益路径不成立。不发车。**

## 2 结论与登记

- **`W27` 三项均判「本机不发车」**，理由为**机制级不匹配**（不是"没测所以不知道"）。
- register `P61`/`P62`/`P63` 的 `verdict` 追加本判定；**status 保持 CANDIDATE**（它们对**其他形态的机器**确实有价值 ---- 这正是 `[EXT]` 车道要表达的）。
- **`[EXT]` 标注**：`P61` -> `[EXT: 小 RAM + 专家多在 VRAM 的机器]`；`P62` -> `[EXT: 显卡还需驱动桌面的机器]`；`P63` -> `[EXT: RAM 装不下完整 KV、或上下文远超 VRAM 的机器]`。

## 3 方法论（可复用）

**「社区实测过」只提供"值得看一眼"，不提供"值得花一车"。** 判据顺序应为：
(1) 读源码定机制 -> (2) 与**本机形态**（RAM 大小 / 谁持有专家 / 有无桌面 / 瓶颈在哪）逐条对照 -> (3) 吻合才设计车。
本次若不复核，三次车约 50 分钟生产时间会全部落在"机制相反"的开关上。


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `a55cca12aa806d770c01a1e9c6687538`（字节 3827）。
