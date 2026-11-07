# W775delta W28C ---- 三级存储机制定稿（显存 / 内存 / SSD）

> 时间：2026-10-11 16:3x　源码：0.1.42（`deploy/tmp/src142/`）　机：单卡 MI50 32GB / 128 GiB RAM
> 用途：把「专家到底放在哪、一次请求怎么流动、为什么 SSD 被读满」从源码定死。

## 0 一句话

专家的三级是 **VRAM 缓存（槽）/ RAM 页锁定补集 / SSD 文件层**。**冷请求的 SSD 读，主因不是"补集装不下"，而是"prompt 路借走的 GPU 缓存槽，其专家没有在 RAM 里留副本，于是每个 chunk 都要从模型文件补回"**。

---

## 1 三层是什么

| 层 | 本机容量 | 装什么 | 谁决定 |
|---|---|---|---|
| **① VRAM —— GPU expert cache** | **9,761 槽（~22.0 GiB）** | 最热的专家（按 `expert-profile` 排名 + `adapt()` 迁移） | `--expert-cache auto`（从 VRAM 预算推） |
| **② RAM —— 页锁定补集** | **33.44 GiB**（旧）/ **36.93 GiB**（含借区，现役） | **base（GPU 缓存装不下的全部专家）+ 借区（若 RAM 还够）** | **[现役 2026-10-11 17:37 起]** `--resident-experts`（无预算）⇒ 借区启用；上限由 `MemAvailable − STRATA_RESIDENT_HEADROOM_GIB(=0.5)` 夹紧（旧：`--resident-budget-gib 76`，设计性关借区） |
| **③ SSD —— 文件层** | **22.0 GiB**（= 总专家 − 补集） | GGUF 分片，**in place 读**（经 OS 页缓存；或 `STRATA_UNBUFFERED_LOAD` 时 O_DIRECT） | 剩下的一切 |

### 1.1 逐字依据

- 三层命名：`docs/DETAILS.md:247-249` *"A RAM budget ... **the rest are read from the files**"*；`UNSLOTH_Q4.md:175` *"Reading a prompt streams every expert once per 4K chunk, and **the third of them outside the RAM budget** [come from the SSD]"*
- 补集选择：`src/core/expert_source.cpp:198-212` `choose_resident_keep_from(slot_bytes, base_bytes, budget, lend_from)`：**base 必须装下**，然后**从最后一个槽往前**加，直到装不下
- 总专家/read 的关系：`expert_source.cpp:1630` `read = expert_bytes() − complement_bytes_`

### 1.2 三个数字自洽（本机现取）

| 量 | 值 | 出处 |
|---|---:|---|
| 总专家 `expert_bytes()` | **55.44 GiB** | `read = experts − complement` 反推（33.44 + 22.0） |
| 补集 `complement_bytes_` | **33.44 GiB** | 日志 `cache complement ready: resident 33.44 GiB, pinned 33.44 GiB` |
| 文件读 `read` | **22.0 GiB** | 日志 `22.0 GiB of experts read from the files` |
| GPU 缓存 | **9,761 槽 x 2.26 MiB = 22.0 GiB** | 日志 `9761 in the GPU cache` |

=> **补集 = base 本身**（33.44 ≈ 33.45 = "experts the GPU cache does not hold"）=> **借区一个槽都没进 RAM**。**（AUDIT4 限定）**：该等式**逐 boot 成立、非恒真** ---- 同一 `--resident-budget-gib 76` 下原始日志实测补集有 **33.44 / 33.45 / 36.80 GiB** 三值（`deploy/tmp/_cold_raw.txt:599/770/815`），随 GPU-cache 槽数与启动可用 RAM 浮动。

---

## 2 一次请求的数据流（含 **borrow / refill**）

```
prompt 到达
  └─ prefill 分 chunk（本机 chunk = 8192）
       ├─ 每层把该 chunk 的 routed 专家过一遍
       │    ├─ 命中 ① VRAM 缓存        -> 最快
       │    ├─ 命中 ② RAM 补集         -> PCIe 搬运
       │    └─ 都没有 -> ③ 从模型文件流  <== SSD 读 + major faults + host staging
       └─ **prompt 路向 GPU 缓存"借"尾部槽当 prefill 缓冲**
            本机：`the prompt path borrows 1554 CUDA0 cache slots (3.49 GiB)`
            （`generate.cpp:7042`；`lend_from = slots - k`，`generate.cpp:6539-6543`）
  └─ prompt 结束 -> **把借走的槽"补回"（refill）**
       ├─ 借区在 RAM 有副本 -> 从 RAM 补回        （= lend region 命中）
       └─ 借区不在 RAM      -> **从模型文件补回**  <== **本机走这条**
```

**机制逐字**（`include/strata/core/expert_source.hpp:115-119`）：
> *"The resident RAM mode: which GPU-cache slots' experts are kept in RAM too. The prompt path lends the cache's LAST slots (from `lend_from` on; a short prompt lends only the last few), and **a lent slot's expert is streamed from RAM during the prompt and copied back into its slot after it**. `base_bytes` (every expert no slot holds) must fit `budget`; slots are then added from the end down to `lend_from` while they still fit."*

`expert_source.cpp:2662-2664`：
> *"The prompt path's lend region: its slots' experts are streamed from here during a prompt and copied back into their slots after it, so the ones that fit are kept here too ... **The rest keep the mapped-file fallback.**"*

`generate.cpp:531-533`：
> *"the prompt path borrows the top expert-cache slots for its buffers and **refills them after the prompt** (default); `--no-prefill-borrow` reserves the buffers' VRAM for the whole session instead."*

---

## 3 为什么 SSD 会被读满（本机的真正原因）

**借区（1,554 槽 / 3.49 GiB）没有 RAM 副本** ⇒ 每次借出，其专家都要**从模型文件补回**；且**每个 chunk 都要流一遍**（`generate.cpp:7064-7066` 上游原文：*"their experts are **streamed from the model file during every chunk**"*）。

**上游自己的量级**（`expert_source.cpp:3111-3113` 逐字）：
> *"#1389: below full coverage the uncovered experts are read from the pack during a long prompt (a 74K prompt routes through nearly all experts, so the misses repeat). The reporter measured **18% uncovered = -26% prompt speed** on a gfx1100"*

**与本机读数吻合**：**110,793-token 冷请求**（`L2569`）耗时 **244.4 s**，其 `file tier` = **OS 从存储读 3,375.7 MB** / 专家读 **79,756.2 MB**。**[AUDIT5-A1 补遗]** 原文把 `OS 从存储读 64,649 MB` 与 `222,659 major faults` 归给同一条请求，实为**另两条**（60-token 首请求 `L2834` / 64,026-token 请求 `L2842`）。

### 3.1 为什么补集没把借区装进去

`choose_resident_keep_from` 要求 **base 先装下，再用剩余预算从尾槽往前加**。本机：
- base = **33.44 GiB**（GPU 缓存装不下的全部专家）
- 补集上限 = `MemAvailable − STRATA_RESIDENT_HEADROOM_GIB`；启动日志：`25.10 GiB really free for a 33.45 GiB page-locked complement; the model files' cached pages were released: 69.71 GiB free`
- 结果：补集 = **33.44 GiB = 恰好 base** ⇒ **剩余预算不足以放进借区（甚至为 0）** ⇒ `keep_from = n_slots`（无借区）

> **注意（AUDIT4 修正归因）**：本链日志确实没有 `keep their experts in RAM too`，但**根因不是"单卡"**。`generate.cpp:7053` 的 `lend sizing` 句（及其 WARNING）**只在 `multi_gpu` 分支打印**；而 `expert_source.cpp:3105-3109` 另有**同义**的一句 `N of M of the prompt path lendable slots keep their experts in RAM too`，仅由 `if (lend)` 守卫、**单卡也打**。我们看不到它，是因为 `budget_bytes > 0`（`--resident-budget-gib`）令 `lend_from_slot = -1` ⇒ **`lend = false`**（`expert_source.cpp:2635/2638`）⇒ 该句根本不打印。=> **一旦改到 `--resident-experts`（OPT-A），这句就会出现，可作借区覆盖的监视行。**

---

## 4 杠杆表（机制 x 上游实测 x 代价）

| 杠杆 | 机制 | 上游实测/原文 | 代价 |
|---|---|---|---|
| **`--no-prefill-borrow`** | prompt 路**不再借**槽 => 没有 refill => **不读文件** | `INTEL.md:248` *"the prompt path must not lend expert slots (a lent expert is served from the host)"*；`INTEL.md:333` *"costs ~1 s on short prompts (2,184 tokens: 610 vs 792 tok/s)"*，故**默认只在 32K 上下文以上借** | prompt 缓冲**自占 VRAM**（~3.49 GiB）⇒ 少若干专家槽 |
| **`STRATA_RESIDENT_HEADROOM_GIB`（默认 4）** | 调小 => 补集上限变大 => **借区可进 RAM** | `expert_source.cpp:3118` 上游直接建议：*"Free RAM or **lower STRATA_RESIDENT_HEADROOM_GIB**"* | RAM 余量变小 |
| **`STRATA_PIN_RESERVE_GIB`** | 同族（`TROUBLESHOOTING.md:120`：默认 = RESIDENT_HEADROOM） | -- | 同 |
| **`--prefill` chunk** | chunk 越大 => 借的槽越多（否则相反） | `DETAILS.md:318` *"the largest chunk whose buffers fit in the expert-cache slots it borrows"* | 已 auto=8192 |
| ~~`--resident-budget-gib`~~ | 补集已 = base，**预算非约束** | 见 §3.1 | **划掉** |
| ~~`STRATA_UNBUFFERED_LOAD=1`~~ | -- | `#773` 实测：无 RAM 预算时强制 unbuffered **重读 163-629 GB、腰斩速度** | **划掉** |
| `STRATA_IO_PREFETCH`（`P54`）/`FETCH_THREADS`（`P46`） | 打"文件层读"这条路 | `#577` | 已重开待测 |

**首选实验（下一车）**：`--no-prefill-borrow`（一刀切断 borrow→refill）对照默认；辅测 `STRATA_RESIDENT_HEADROOM_GIB` 调小（让借区进 RAM）。两者**同路径不可组合**（W723）。

---

## 5 复现命令

```bash
# 三层与借区
grep -a 'FileExpertSource:'      /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'borrows'               /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'cache complement ready' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'file tier I/O this request' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
# 系统侧
curl -s 'http://127.0.0.1:19999/api/v1/data?chart=disk.sda&after=-172800&points=1440'
```
