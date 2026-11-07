# 向上游（Niko1221/Strata）可提交的东西 —— 逐条核查过重复性

- 日期：2026-10-27 01:15
- 方法：每条候选都先在 `repo:Niko1221/Strata` 的 issue/PR 里检索过（含 `deterministic`、`reproducible`、
  `ple resident evicted`、`mmap prefetch page fault`、`O_DIRECT arena`、`timing guess` 等查询），
  下表的「现状」一列是**实际查到的编号与状态**，不是我猜的。
- 排序依据：**对别人的价值 × 我们证据的强度 ÷ 提交成本**。

---

## 建议提交（4 条）

### C1　[Engine] Greedy output is not reproducible: six identical requests, three to five different answers

- **形式**：新 issue（缺陷报告，非 PR）。上游模板要求标题带 `[Engine]` 前缀。
- **现状**：**未覆盖**。最接近的是 **#4106**（open，Strix Halo，v0.2.4）——它比的是 Strata 与 llama.cpp 的
  greedy 吻合率（5/24），**没有人报过"同一个引擎、同一个进程、同一输入，连发就不同"**。#4106 的后续
  （`--expert-cache 24576` 全驻留后任务分与 llama.cpp 一致）也没触及这一点。
- **我们的证据**：
  - 三次独立启动，每次在**同一进程内**连发 3 次（64 token）：B1 **3/3** 不同、B3 **3/3**、B2 2/3；
    三臂的 chunk 逐字相同（`lent 191 slots for 256 tokens`）⇒ 与启动期选路无关。
  - 96 token 连发 6 次：**3 个答案、非单调**（`R0=R3=R4`(554 字) / `R1=R2`(528) / `R5`(558)），
    最早分岔在第 **~13 token**，呈多吸引子。
  - `temperature 0` 确实是贪心：`serve/server.py:957-958` 逐字「`temperature=0` means the same thing,
    so it is not forwarded」，引擎侧 `generate.cpp:7052` `if (sp.greedy || sp.temperature <= 0.0f)`。
  - 已排除的替代解释：专家档案（读镜像内固定文件、`learned.bin` 只写不读）、`--spec 0`（native IQ pack
    硬要求 `T>=2`，见 P144）、`STRATA_ROUTE_TAIL_SKIP=0`（**反而更差**：6 次出 5 个）。
- **价值**：这决定所有"逐字比较"的用户级用法（代码、测试、回归）是否可信；也会解释 #4106 那类报告。
- **成本**：低（现成的 3 个原始件 + 一个 40 行客户端）。**风险**：上游可能答"这是浮点归约的固有行为"——
  那就把问题收敛成"请在文档里写明 greedy 不可复现"，仍是净收益。

### C2　[Engine] PLE `gather()` has a Windows prefetch but no POSIX one: mmap decode pays 16 serial page faults on Linux

- **形式**：小 PR（约 10 行）。
- **现状**：**未覆盖**。检索 `mmap prefetch page fault decode` 只命中 #2101/#2040/#1984（都是
  "mmap 让 decode 变慢"的**故障报告**，没人指出源码里的这个不对称）。
- **逐字依据**（`src/kernels/ngram.cpp`）：
  - `gather_batch`（提示路径）有 `hint()`，Windows 走 `PrefetchVirtualMemory`（:601），POSIX 走
    `madvise(MADV_WILLNEED)`（:607）——**两条都有**。
  - `gather`（解码路径，单 token）:665-675 的 `PrefetchVirtualMemory` **在 `#if defined(_WIN32)` 里**，
    **POSIX 一个 hint 都没有**，直接进 16 次串行 `read_row`。
  - 源码自己的注释（:645-660）：「**THIS COST 2.10-2.61 ms PER TOKEN** … sixteen reads into sixteen
    different 4 KB pages … taken ONE AT A TIME」，并说 Windows 上靠 `PrefetchVirtualMemory` 解决。
- **补法**：在 `gather` 的读循环前，对 16 个 `rows16[h]` 的页做与 `hint()` 同样的 `madvise(MADV_WILLNEED)`
  （16 次廉价系统调用，内核异步发起），Windows 分支保留。
- **价值**：直接削弱 #2101 报的「mmap decode -20~-25%」，也就是上游至今把 `STRATA_PLE_AUTO_MMAP` 默认关掉的理由之一。
- **诚实的边界**：我**没有**在本机测到收益——我们的盘是 SATA，跑的是 `direct`，mmap 与 direct 只差 1.7%。
  所以 PR 里必须写清"这是对齐，不是本机实测收益"，并请 NVMe/loop 设备用户验证。

### C3　评论：`#3624`（Linux 竞技场 O_DIRECT）—— 补上"它还会毁掉 PLE 表"这条理由 + 我们的数据

- **形式**：在 **#3624**（open PR）下留一条评论，不新开 issue。
- **现状**：#3624 的理由只有"更快"（他们在 NVMe RAID0 上 5.7 → 12.0 GiB/s，就绪快 4 s）。**没有**人提到
  缓冲读会冲刷页缓存。
- **我们的证据**：`--ple-io ram` 把 26.8 GiB 表 touch 进页缓存后，**同一次启动里**的
  `loaded 55.43 GiB at 0.35 GiB/s`（Linux 恒走页缓存，`pinned.cu:827` 逐字 `why = "buffered (not Windows)"`）
  会把表挤掉：跑完 `RssFile` 只剩 **986 MB**，宿主 `Cached` 78.6 → 43.8 GB。
  ⇒ `--ple-io ram` 从 -14% 退化到 **0%**（同一臂第 1 个请求 PLE=8 ms，第 2 个起回到 641 ms）。
  启动前 `drop_caches` 才留得住（`PLEMAP` 稳定 25.0-26.5 GiB）。
- **价值**：给 #3624 一个**正确性/功能**级别的理由（不只是性能），并给 #3357（RAM 静态估算）补上
  "静态够 ≠ 运行期留得住"。成本：一条评论。

### C4　[Engine] `--ple-io ram` never checks that the table is still resident: a 26.8 GiB table falls out of RAM and the mode silently becomes direct

- **形式**：新 issue（可与 C3 互引）。
- **现状**：**未覆盖**。#4104 是"touch 太慢（310 s）"，#4105 是"用 O_DIRECT 读进 page-locked RAM"，
  #3357 是"setup 的静态容量判断算错了"。**没有**一条说"启动之后表会掉出去，而且没有任何提示"。
- **我们的证据**：`PleTable::locked()` 只在 `mlock` 成功时置位；本容器 `ulimit -l = 8 MB`，`mlock` 必失败
  （日志逐字 `PLE table mlock failed (Cannot allocate memory; raise ulimit -l)`），于是表只是普通文件页，
  被竞技场那 55.43 GiB 的顺序流冲掉。**日志里没有任何一行**说它掉了——`PLE table loaded (not locked) in 84.2 s`
  之后就没消息了。
- **建议的修法**（二选一，都很小）：
  ①启动收尾时对映射做一次 `mincore()` 抽样，常驻率低于阈值就打一行 warning（"the table is 34% resident,
  `--ple-io ram` is not in effect"）；
  ②或把 `PleIoOptions` 的 `locked` 语义扩成 `resident`，并在 `io_report` 里报常驻率。
  成本低、可测（我们有 `PLEMAP` 的前后对照）。

---

## 可以提交但优先级低（3 条）

### C5　[Docs] startup VRAM staging: 8.79 GiB is everything-but-the-expert-cache
- 一页表格：`0.01 → 3.70 → 8.79（平台）→ 31.04 → 31.41 GiB`，`8.79 + 22.25 = 31.04` 与日志逐字吻合；
  平台长度 = 竞技场载入（冷 0.27-0.40 GiB/s / 热 3.0-4.5 GiB/s）。上游 docs 里没有这张"启动轨迹"表，
  而"显存卡在 8.8 GiB 是不是漏了"这类问题很容易被反复问。
- 现状：未覆盖。形式：docs PR（`docs/DETAILS.md` 或新 `docs/STARTUP.md`）。成本：低。

### C6　[Benchmark] SATA SSD: the PLE channel is 13-15% of prefill and 93.6% of it is waiting for the disk
- 数字：`ple` 在 2.5-5K 提示上占 **12.9-16.7%**；无盘时主机侧 PLE **15.8 ms/1k**、有盘 **250 ms/1k**
  ⇒ 折合 **68k rows/s = 280 MB/s 随机 4 KiB = 68k IOPS**（SATA 队列到顶）。
- 四臂结论（同一语料、跨臂逐字同一文本）：`mmap` -1.7%、`ram` 裸用 0%、`--ple-row-cache` 1M→4M 0%、
  `--prefill 2048` 让 PLE 掉到 6.8% 但总时间 +5.3%、`--no-ple-prefetch` +1.4%。
- 现状：上游 docs 有 ple-io 的行为描述，但**没有 SATA 盘的量化**，也没有"每 1k token 多少毫秒"这一列。
- 形式：`[Benchmark]` issue（社区报告格式）。成本：中（要整理成他们的报告模板）。

### C7　[Docs] 把「chunk 大小 ↔ PLE 重叠」这条机理写进 `--prefill` 的说明
- 机理：`ple_reader.hpp:5-14` 逐字「a chunk's reads can run while the previous chunk computes」⇒
  只有第一个 chunk 付 PLE。实测 2048 让 `ple` 从 14.7%→6.8%，但总时间 +5.3%（chunk 边界更贵）。
- 现状：0.2.5 的说明只有「cold 8K prompt is 9% slower」，没有机理；docs 也没有。
- 形式：并入 C6 或单独 docs PR。成本：低。

---

## 不建议提交（会被当成噪音或已被覆盖）

| 候选 | 为什么不提 |
|---|---|
| `--spec 0` 被拒绝 | 有意为之（native IQ pack 要求 `T>=2`），是设计不是缺陷；最多算文档补充 |
| `STRATA_UNBUFFERED_LOAD=1` 在 Linux 无效 | **#3624 正文已经写明了**（只抬 reader 数），提了就是重复 |
| `--ple-io mmap` 在 SATA 上更慢 | **#2040 已报**（SATA 上 mmap 2.1K 对 direct 14.4K） |
| `--ple-io ram` 启动慢 | **#4104 已报**（310 s / 90 MB/s），我们的 85 s 只是同现象的另一个数字 |
| PLE 表 mlock 失败 | 环境限制（`ulimit -l`），上游 INTEL.md:723 已明确建议**不要**调大 |
| gfx906 的 `arch_default` 空表 | 上游对非目标架构不填表是有意的；我们的量级（CPU share、RT_SKIP）已在 0.1.41+ 覆盖 |

---

## 归属核对：哪些是**我们真做的**，哪些只是复述上游

> 这张表是给自己对账用的：**只有 A 类可以当作"我们的发现"去提**；B 类只能以"补充数据/证实"的口吻出现；
> C 类提了就是噪音。

### A 一手原创（上游没有对应记录，或方向相反）

| # | 结论 | 一手证据 | 备注 |
|---|---|---|---|
| A1 | `ple` 占 prefill **12.9-16.7%**（2.5-5K），**250 ms/1k token**，其中 **93.6% 是等盘**；折合 **68k rows/s = 68k IOPS**，SATA 到顶 | `W810_PLE_IO.md` §2 | 上游 docs 只有行为描述，没有 SATA 量化，也没有"每 1k token 多少 ms" |
| A2 | `--ple-io ram` **裸用 = 0%**：表被竞技场那 55.43 GiB 缓冲流挤掉（`RssFile` 986 MB、宿主 `Cached` 78.6→43.8 GB） | `W810` §2.3 | #3357 只做**静态**容量判断；没人说"启动之后会掉出去且无提示" |
| A3 | `ram` + **启动前 `drop_caches`** = 提示 **-12% ± 4%**（三会话六格：-14.0/-14.7、-4.3/-13.7、-9.2/-15.5），解码 -1.1%（噪声内）、槽位 9873 不变 | `W812/813/814` | 独家配方与数字 |
| A4 | `--prefill 2048` 让 `ple` 从 **14.7%→6.8%**（机理：只有第一个 chunk 付钱）但**总时间 +5.3%** | `W812` §3.1 | 上游只有"4096 冷 8K 慢 9%"，没有机理与 PLE 量化 |
| A5 | `--ple-row-cache` **拐点在 1M**：设 0 掉 15-20%，4M 零收益 | `W810` §2.2 | 上游只有"1M 可服务 82%"的模型估计，无实测臂 |
| A6 | 启动 **8.79 GiB 平台 = 全部上卡显存 − 22.25 GiB 专家缓存**；`8.79+22.25=31.04` 与日志逐字吻合 | `W815` | 独家；可作 docs 素材 |
| A7 | 本机启动两档：**冷 0.27-0.40 / 暖 3.02-4.47 GiB/s**（SATA） | `W815` §4 | #3624 是 NVMe RAID0（5.7/12.0），不同档位 |
| A8 | `ngram.cpp` 的 `gather()`（解码路径）**只有 Windows 预取，POSIX 一个 hint 都没有**，而 `gather_batch` 两条都有 | 源码 :665-675 对照 :601/:607 | 独家源码发现，C2 的全部依据 |
| A9 | 贪心**同进程内不可复现**的量化：6 次 3-5 个答案、最早 **~13 token** 分岔、**多吸引子**；且 `RT_SKIP=0` 更差、`share=0` 依旧（4/6） | `W816`/`W818`/`W819` | 上游只有 #4106 的"与 llama.cpp 差"；**自身不一致无人报** |
| A10 | `--learned.bin` **只写不读**；`--ple-io ram` 从不校验常驻（`locked()` 只反映 mlock） | 源码/日志 | 小观察，C4 的依据 |

### B 我们做了，但结论归上游（只能当"补充数据"讲）

| 结论 | 上游出处 |
|---|---|
| Linux 竞技场载入走页缓存、`STRATA_UNBUFFERED_LOAD` 在 Linux 只抬 reader 数 | **#3624** 原文 |
| `--ple-io ram` 的逐页 touch 很慢（310 s / ~90 MB/s） | **#4104** |
| `mlock` 需要 `ulimit -l`，容器里建议不要开大 | `docs/INTEL.md:723` |
| SATA 上 `mmap` 更慢 | **#2040**（**注意：我们没复现出 7x**，只测到 ≈direct，见下） |
| `mmap` 让解码变慢 | **#2101**（**我们没复现**：48.27 / 48.38 对 47.28-51.52，噪声内） |
| 贪心输出与 llama.cpp 不一致 | **#4106** |
| `--spec 0` 被引擎拒绝（native pack 要 T≥2） | 设计如此，非缺陷 |

### C 需要**收缩措辞**的一条（内部早有半条）

`W802/W803` 的登记里已经写过「**开 share 后 prefill 逐次不同**」「share=0 时两遍 md5 完全相同」——
所以"同请求不同字节"这件事**不是今晚才发现的**。今晚新增的是三件事：①它**在决策级**（贪心文本，不只是字节）；
②即使 `share=0` 也仍在（W819 实测 4/6）；③它的结构（多吸引子、~13 token 分岔、跨启动也不同）。
⇒ C1 里必须写这个来龙去脉，不能把"发现不可复现"整个揽成今晚的成果。

### D 明确**没做成**的（不要写成结论）

- **C2 的收益**：本机 SATA + `direct`，测不出 mmap 预取带来的好处；只能证明"不改行为"。
- **C1 的根因**：只排除到"share / 尾跳 / 启动选路 / 档案"四项，剩下的"批形状 / 驻留集合"是**推测**。
- **mmap 在 SATA 上更慢（#2040）**：我们 1.5-5K 的提示上测得 mmap ≈ direct（-1.7%），
  与 #2040 的 77.8K 长提示不在同一区间，**不能拿来反驳，也不能拿来支持**。

---

## 需要你定的三件事

1. **署名与身份**：用哪个 GitHub 账号发？issue 里要不要写"on a gfx906 (MI50) box"这类硬件信息？
2. **C2 要不要真做**：我可以写出补丁并在本机构建、跑 `ple_parity` + 我们自己的 decode 门，
   但**收益在本机测不出来**（SATA + 走 direct），只能证明"不改行为、只加 hint"。你要不要这种"对齐型 PR"。
3. **顺序**：我建议 **C1 → C3 → C4 → C2**（先拿最硬的一条确立可信度，再借评论挂上 C3/C4，最后才提 PR）。

---

## 已经写好的草稿（可直接贴）

| 文件 | 内容 | 状态 |
|---|---|---|
| `deploy/upstream/C1_greedy_not_reproducible.md` | C1 的完整 issue 正文，已按上游 `bug_report.yml` 的字段组织（Area / Docker / What happened / Smallest steps / Reproduction status / 版本 / 硬件 / 模型 / 日志），含两张结果表与"已排除"清单 | 待你过目后发 |
| `deploy/upstream/C3_comment_3624.md` | C3 的评论正文（英文），含冷暖两档载入速率表、"缓冲读把 PLE 表挤掉"的实测链，以及对 PR 的两个具体提问 | 待你过目后发 |

两稿都只用**实测数字 + 源码行号**，没有推测性结论；不确定的地方（C2 的收益）明确写成"本机测不出来"。

---

> ### ❌ C4 已撤回（2026-11-01 20:5x，同日）
>
> **不要提交这一条。** 复查发现引擎**本来就有前缀缓存**：`conversation_prefix()` 就是前缀匹配，
> `ConversationCache::best()` 取最长前缀，`borrows()/take()` 分派借还是接管。
>
> 真实多轮对话（`[user P1][assistant reply][user P2]`）实测 **1867/2336 = 80% 复用**，
> TTFT 从 3750 → 1586 ms。§9 里那个「0 复用」是我探针的构造错误——第 2 轮没带模型自己的回复，
> 于是第一个新 token 就与 parked 状态分叉。
>
> 保留这一节只作**教训**：**给上游报缺陷之前，先确认自己的复现是真实负载形态。**
> 剩下的真问题在恢复开销（~830 ms/次），见 `W863_PREFILL_TTFT.md §10`，那是另一个候选。

## 追加候选（2026-11-01 20:3x）· C4 · 前缀增长的 prompt 复用

**问题**：多轮对话每轮都付全量 prefill，即使引擎里已经存着上一轮的 KV。

**实测证据**（本机，`deploy/W863_PREFILL_TTFT.md §9`）：

```
prompt 3066 tokens = 0 reused    + 3066 read in 4747 ms   ← 第一次
prompt 3066 tokens = 3061 reused + 5    read in  225 ms   ← 完全相同的 prompt
prompt 2903 tokens = 0 reused    + 2903 read in 4546 ms   ← 上一轮 + 400 新 token
conversation cache: parked=4 bytes=1083214768 reused_kv_bytes=0
```

同一台机、同一个引擎：**整段相同 → 99.8% 复用（快 21×）；只多 400 token → 0 复用、全量重算**。
缓存里 parked 4 个对话、1.08 GB，`reused_kv_bytes` 恒为 0。

**定位**（源码核实，不是推测）：

- `generate.cpp:14222` 的恢复循环只遍历 `checks`（已按会话过滤的检查点），
  条件是 `c.ids.size() > resume && starts_with(c.ids, c.imgs)`，**没有与当前 prompt 比对前缀**；
- `STRATA_SLOT_CKPT_MOVE` 的注释原文是 **"a second request with the same history"**
  ⇒ 整条机制的设计前提是「历史完全相同」，不是「历史增长」；
- `--prompt-cache-every` 只决定"多久打一个检查点"。实测把它从 8192 降到 1024 **完全无效**
  （turn2/全新 99% → 100%，n=3，CV 1%），而且 10K 的 prompt 会因此打 9 个检查点、纯属浪费。

**建议的改法**（最小、幂等、不改数值）：

恢复时允许"检查点是当前 prompt 的前缀"——即在 `resume` 的候选里，除了 `c.ids == live[0:L]`
再接受 `prompt[0:c.ids.size()] == c.ids`。K/V 来自同一个检查点、同一段 token 位置，**输出逐位相同**。

**为什么值得提**：这是 vLLM APC / SGLang RadixAttention 的标准行为（vLLM 默认 block_size=16，
前缀按块匹配；SGLang 精确到 token）。多轮对话在业内的预期收益是 TTFT 降 30–55%。
我们这边是**完全不复用**，所以这一条对任何多轮用户都成立，不只对我们这张卡。

**现状**：未提。需要先确认上游是否已在 issue 里讨论过（检索词：`prefix`、`checkpoint`、`resume`、
`prompt cache multi-turn`），避免重复。
