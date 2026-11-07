# W775delta W28D ---- 冷路径优化方案（基于三级存储机制）

> 时间：2026-10-11 16:4x　上游：`#1670` 更正已发（`6107050493`）
> 依据：`W775delta_W28C_THREETIER_MECHANISM.md`（三级机制定稿，0.1.42 源码）

## 0 结论（根因一句话）

**我们现在用的 `--resident-budget-gib 76` 这个 flag 的设计本身就"没有借区"** ⇒ prompt 路借走的 1,554 个缓存槽，其专家**永远从模型文件补回**。上游源码逐字：

> `include/strata/core/expert_source.hpp:550-552`
> *"CS-T, `budget_bytes` > 0 (`--resident-budget-gib`)：只复制装得下的那部分，其余留在映射文件上（SSD 层）。**No lend region then (a lent slot's expert is read from the files).**"*

**⇒ 优化 = 换掉这个 flag，改用 `--resident-experts`（无预算形态）并给借区腾出 RAM。**

---

## 1 根因链（四步，全部源码/日志）

| 步 | 事实 | 依据 |
|---|---|---|
| 1 | `--resident-budget-gib` 置 `resident_cpu_experts = true` 且 `resident_headroom = 4 GiB` | `generate.cpp:2077-2082` |
| 2 | 但 **`budget_bytes > 0` ⇒ 借区被设计性关闭** | `expert_source.hpp:550-552` |
| 3 | 实际预算 = `available − headroom`，**不是 CLI 的 76** | `expert_source.cpp:2649-2650` `budget = available - headroom_bytes` |
| 4 | 补集恰好 = base（33.44 GiB，**AUDIT4：逐 boot 成立、非恒真** ---- 同 flag 下实测 33.44/33.45/36.80 GiB，36.80 那 boot GPU-cache 仅 8,268 槽）⇒ `budget − base ≈ 0` ⇒ 无余量放借区 | 日志 `allocating 33.45 GiB` + `resident 33.44 GiB` |

**反推启动时的可用 RAM**：`budget(33.44) + headroom(4.00) = **≈37.44 GiB**`（推断值，非直读）⇒ 借区要 3.49 GiB，**被那 4 GiB headroom 正好吃掉**。

**⇒ 两件事都要做**：(a) 换 flag 让借区机制启用；(b) 降 headroom（或加 RAM）让借区有位置。

---

## 2 量化（本机现取）

| 量 | 值 | 说明 |
|---|---:|---|
| base（GPU 缓存装不下的全部专家） | **33.44 GiB** | 日志 |
| 借区（prompt 路借的 1,554 槽） | **3.49 GiB** | 日志 `borrows 1554 CUDA0 cache slots (3.49 GiB)` |
| **要让借区进 RAM 所需** | **36.93 GiB** | base + 借区 |
| headroom 默认 | **4 GiB** | `generate.cpp:2069/2082` |
| ⇒ 需要 `available ≥ 36.93 + headroom` | 现 headroom=4 ⇒ 需 **40.93 GiB** 而当时只 ≈37.44 | **差 ~3.5 GiB** |
| 现 MemAvailable | **83.58 GiB** | 现在很宽裕（启动那一刻不是） |
| 常驻容器占用 | comfyui 1.29 + open-webui 1.01 + netdata 0.57 + searxng 0.16 + portainer 0.08 = **~3.11 GiB** | 可腾 |

---

## 3 优化方案（按机制强度排序）

| # | 方案 | 机制 | 预期 | 代价/风险 |
|---|---|---|---|---|
| **OPT-A（主推）** | `--resident-budget-gib 76` → **`--resident-experts`**（去预算）+ **`STRATA_RESIDENT_HEADROOM_GIB=0.5`** | 去预算 ⇒ 借区机制启用；降 headroom ⇒ `available−headroom` 余量 ≥ 3.49 GiB | **借出的 1,554 槽专家留在 RAM ⇒ refill 从 RAM ⇒ 冷路径 SSD 读基本消失** | RAM 余量 −3.5 GiB；需确认不触发 OOM / 不进 what-fits 退化 |
| **OPT-A+** | OPT-A **再腾 RAM**（停 comfyui/open-webui ≈2.3 GiB，或启动前 `drop_caches`） | 把 `available` 抬到 ≈39.7 GiB ⇒ 余量 5.8 GiB（舒服） | 同 OPT-A，但**不靠压 headroom 到极限** | 要停别人的容器（需你同意） |
| **OPT-B** | `--no-prefill-borrow` | prompt 路**不借**槽 ⇒ 无 refill ⇒ 不读文件 | 同效，另一条路 | prompt 缓冲自占 VRAM ~3.49 GiB（少专家槽）；上游 `INTEL.md:333` 短 prompt ~1 s |
| **OPT-C** | `--prefill` 固定较小 chunk（如 4096） | 借区大小 ∝ chunk ⇒ 借区减半(≈1.75 GiB) ⇒ **更容易进 RAM** | 借区可覆盖面变大 | chunk 变小 ⇒ chunk 数变多 |
| **OPT-D** | 启动前 `drop_caches` / 先起引擎再起别的容器 | 提高引擎测得的 `available` | 间接放大预算 | 只影响启动那一刻的读数 |

> **划掉**：`--resident-budget-gib` 调大（设计上无借区，调大无用）· `STRATA_UNBUFFERED_LOAD=1`（上游 `#773` 实测腰斩）。

---

## 4 上游自己的量级（告诉我们值不值得做）

`expert_source.cpp:3111-3119` 逐字（WARNING 文本）：
> *"#1389: below full coverage the uncovered experts are read from the pack during a long prompt (a 74K prompt routes through nearly all experts, so the misses repeat). The reporter measured **18% uncovered = -26% prompt speed** on a gfx1100; short prompts barely touch them."*
> *"... expect a slower prompt read on 50K+ token prompts (one measurement: **18% uncovered cost 26%**)."*

本机现状：**借区 100% 未覆盖**（1,554/1,554）⇒ 量级只会比 18% 更重。本机实测冷请求 `read_ms` 中位 **12.6 s / 最大 252 s**。

---

## 5 车设计（验证 OPT-A）

**两臂（A = 现行 / B = 候选），一次停-起：**

| 臂 | 专家侧 args | env |
|---|---|---|
| **A（基线）** | `--resident-budget-gib 76` | （现状，无） |
| **B（候选）** | **`--resident-experts`**（去掉 budget） | **`STRATA_RESIDENT_HEADROOM_GIB=0.5`** |

**判据（两级，先二元后量化）**：
1. **二元硬证（启动行，不看速度）**：B 臂 `allocating %.2f GiB page-locked cache complement` 应 **> 33.44 GiB（≈36.9）** ⇒ 借区确实进了 RAM。（单卡下 `N of M lendable slots` 那行不打印，见 `generate.cpp:7053`）
2. **量化**：按**新口径** —— 请求级 wall time 分 **C 冷 / W 温**，每请求记 `prompt ... read in ms` + `file tier I/O this request` + **并行系统遥测**（GPU/CPU/iowait/disk）；报 **p50/p90/max**；ABBA ×5。

**若 B 臂出正果** ⇒ 走 register 通道固化：`P65`/新增 `--resident-experts` 行 → `gen_config.py --write` → 推 166 → restart → `verify_config FAIL=0`。

---

## 6 风险与边界

- **RAM 余量 −3.5 GiB**：headroom 0.5 属偏紧；若引擎后续分配触发 OOM 或 `what-fits` 退化，回退 headroom=2 + OPT-A+ 腾 RAM。
- **答案是否变**：`--resident-experts` 与 budget 形态**同一份专家字节、同一放置**，上游 `generate.cpp:6492` 逐字 *"the bytes are the file's bytes and the placement is the same, so **the answers are the plain mmap mode's**"* ⇒ **不改答案**（低风险）；仍按纪律做 parity 门。
- **同路径不可组合**（W723）：OPT-A 里"去 budget"与"降 headroom"是**一个协同配置**（去 budget 才让借区机制存在），故作为**一个候选配置** A/B；OPT-B/C 各自单独成车。

---

## 7 复现命令

```bash
# 启动行（借区是否进 RAM 的二元判据）
grep -a 'allocating .* cache complement' /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'cache complement ready'          /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'borrows'                         /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
# 冷路径读数
grep -a 'strata serve: prompt [0-9]'      /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
grep -a 'file tier I/O this request'      /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
```

---

## 8 补：`P46` 逐项（**冷路径视角**）+ 命中率口径 + **第三条机制（stager 档）**

> 机主追问：「P46 的你都考虑了？IO_PREFETCH？我不是说了命中率的问题？」---- 本节是据实补齐。

### 8.1 `P46` 族 **逐项**（此前只按族重开，未逐项判）

| 键 | 默认 | 作用于 | **冷路径是否是杠杆** | 依据 |
|---|---|---|---|---|
| `STRATA_FILL_AHEAD` | 256 | **启动时的 profile 填充**（"the profile fill asks for N pairs ahead"） | **否**（不覆盖每请求的 prompt 读）；但**影响启动**（本机某次预填 64.5 s @366 MB/s） | `generate.cpp:5047-5053` |
| `STRATA_FS_AHEAD` | 1（需 swap 空间开） | Foresight swap 的预测 | **否**----**未激活**（我们没设 `STRATA_FS_SLOTS>0`） | `generate.cpp:5386-5387`；`foresight_swap.hpp:2` |
| `STRATA_FETCH_THREADS` | 8 | **"while it answers"= 回答期（decode）**读线程 | **不是 prompt 那把**----**prompt 路另有 stager**（上游逐字：*"The prompt path has its own: `STRATA_STAGER_THREADS`"*） | `UNSLOTH_Q4.md:235-236`；`generate.cpp:4522` |
| `STRATA_IO_PREFETCH`（=**P54**） | 关 | Linux 文件层：whole-blob preads + 预测层 I/O 线程（`STRATA_IO_PF_THREADS` 默认 8，`_DEPTH` 默认 2） | **是**（直接打文件层）----**但 W773 的"预取 0 次"是温窗读数**，冷路径下预测的专家**不在页缓存** ⇒ 有活可干 | `DETAILS.md:225-227`；`generate.cpp:4560-4565` |

**⇒ 结论修正**：`P46` 族里**只有 `IO_PREFETCH` 是对冷路径的**；`FETCH_THREADS` 是**decode 期**的（名字容易误读）；`FILL_AHEAD` 是启动期的；`FS_AHEAD` 未激活。

### 8.2 命中率 ---- 机主这条**完全成立**

- 引擎**唯一的命中率行**是 **`decode expert cache hit rate`**（**decode 口径**）。
- **prompt 阶段没有任何命中率行** ⇒ 我们此前引的 95-98% **只描述 decode**；**prompt 期的命中/未命中从未被度量**。
- 冷请求的表征只有 `prompt N tokens = R reused + K read in MS ms` 与 `file tier I/O this request`。
- ⇒ **W28 的"新口径"必须补一项：prompt 期未命中量的量化**（现有可用量 = `read_ms` + `file tier I/O` 的 MB/major faults）。

### 8.3 第三条机制（**新发现，且很可能是你那次的主因**）：stager 档选错

`src/prefill/prefill.cpp:1054-1083` 逐字：

- *"most of a chunk's blobs are **page faults on the SSD**, so the copies need many reads in flight —— **32 threads and a 128-deep ring read a 4K chunk in 29 s instead of 71 s** ... (4 threads, 16 deep: **the defaults**)"*
- 选择逻辑：`files && !stv` 时用 `src->cached_share(256)` 抽样；**>=90% 在页缓存 ⇒ 降级为 RAM profile**（4 线程 / 16 深 / batch 1）
- 官方覆盖开关：**`STRATA_STAGER_SSD=1`**（注释逐字 *"force the profile (A/B, support)"*）· `STRATA_STAGER_THREADS`（1-32）· `STRATA_STAGER_RING`（2-256）· `STRATA_STAGER_BATCH`

**本机实测（产线现取）**：
```
30  prefill: the GGUF experts are 100% in the page cache; the stager takes the RAM profile
```
即 **30/30 次启动全部取 RAM profile**（4 线程 / 16 深）。而同一 boot 的 GPU 预填实测 **64.5 s @ 366 MB/s**（真磁盘速度）⇒ **页缓存并不真的长期持有**，但 stager 已按"100% 温"降级。

行号顺序（最后一次启动，实测）：`释放页缓存(3547)` -> `补集建好(3554)` -> `borrow(3558)` -> **`stager 抽样(3614)`** ⇒ 抽样在释放之后，但**补集复制 + GPU 预填又把 ~55 GiB 读回页缓存**，故抽样时确实"温"----**问题在于该状态不持久**，之后 prompt 读落到磁盘时，stager 仍是 RAM 档。

**⇒ 这条直接解释你的观测**：`GPU 等（缺专家字节）` + `CPU 满载（staging 但只有 4 线程）` + `磁盘拉满（真读）`。

### 8.4 新增优化项

| # | 方案 | 机制 | 依据/代价 |
|---|---|---|---|
| **OPT-E（与 OPT-A 并列主推）** | **`STRATA_STAGER_SSD=1`**（或 `STRATA_STAGER_THREADS=32` + `STRATA_STAGER_RING=128`） | 强制 SSD 档：**file-tier 读并行度 4->32 线程 / ring 16->128** | 上游同条件实测 **29 s vs 71 s（一个 4K chunk）**；反向代价：若页缓存真温，32 线程比默认 **慢 4-7×** |
| **OPT-F** | `STRATA_IO_PREFETCH=1`（`P54` 冷路径复测） | whole-blob preads + 预测层 I/O 线程 | W773 的"0 次"是温窗；需冷路径重测 |

**⇒ 车设计更新（B8）**：三臂**不可组合**（W723），须各停一次：
- **B7** = OPT-A（`--resident-experts` + `STRATA_RESIDENT_HEADROOM_GIB=0.5`）---- 治 **M1/M2（覆盖）**
- **B8** = OPT-E（`STRATA_STAGER_SSD=1`）---- 治 **M3（staging 并行度）**
- 之后再看 `IO_PREFETCH`（B6）
