# W786 方案目标纠正：从"decode 提速"转到"端到端等待时间"

> **[2026-10-25 05:4x 勘误，见 `W787_R1_FAILURE_REVIEW.md`] 本文有两处错，都已由实测推翻：**
> 1. **R1（对话复用）撤销。** 补丁正确编译（`1 checkpoints` 有日志）、生产也切过，
>    但**真实复用一直是正常的**——`0.2.4` 无补丁下真实多轮第 2 轮 `reused=7,344`、`prompt_ms 15,330 -> 685`（22 倍）。
>    「8K 以下零复用」是三个测试脚本构造错误的产物（分支场景 / 加标签破坏前缀 / ctx 重复两次）。
>    补丁存下的整段 checkpoint 还会被 park 时的 `drop_superseded` 删掉（`generate.cpp:9492`）。
> 2. **§1 的推论只对"单轮"成立。** 多轮追问时 prefill 已被复用压到 0.6 s，**decode 是大头（长输出时约 99%）**。
>    所以 §4 把 GEMV(13.3%)/router(8.1%)/HC(16.1%) 降级为"端到端 0.2-0.4%" 是错的，它们在多轮场景里就是 13.3%/8.1%/16.1%。
> **仍然成立的部分**：三档 decode 基线（§2.1）、prefill 是算力地板（§2.2/2.3）、旧表 P87 作废（§2.1 末）。
> 队列以 `W787 §4` 为准：R5(HC 16.1%) -> R3(GEMV 13.3%) -> R4(router 8.1%) -> R2(溢出) -> R6(注意力) -> R8。

> 缘起：机主令「根据审计结果，调优方案需要跟着调吗」。
> 结论：**要调，而且不是数字层面——优化目标本身就选错了。**
> 本文取代 `W785 §1 的上限表与队列`，`W785` 转为历史留档（映射见 §6）。

---

## 1 一句话结论

`W776` 到 `W785` 五个版本的队列，全部在优化 **decode**（46.35 ms/window）。但实测三档端到端构成：

| 档 | prompt | prefill | decode | **prefill 占墙钟** | decode 占墙钟 |
|---|---|---|---|---|---|
| S | 2,813 | 6.5 s | 4.9 s | **57%** | 43% |
| M | 21,827 | 44.4 s | 5.1 s | **90%** | 10% |
| L | 99,387 | 211 s | 1.1 s | **99.5%** | 0.5% |

=> **decode 提速 10%，在 M 档只换来端到端 1%；prefill 提速 10%，换来 9%。**
=> 更狠的一条：**对话复用的修复能给 M 档第二轮省 44 s（快 88 倍），而任何 kernel 优化最多给它 1%。**
> **[2026-10-25 05:4x 勘误] 上面这句是错的。** 复用本来就能用（真实多轮第 2 轮 `reused=7,344`、`prompt_ms 15,330 -> 685`），不存在"从未复用"；而且这条推论只对**单轮**成立——**多轮追问时 prefill 已降到 0.6 s 量级，decode 才是大头**。详见 `W787_R1_FAILURE_REVIEW.md §3`。

---

## 2 新证据（三条，都是本轮实测）

> **【2026-10-25 15:4x 勘误（`W792`）】** 本件的"端到端"三档占比（decode 10%/0.5%）仍然成立，但**表内 prefill 数字已过期**：
> `STRATA_HIP_PROMPT_F16=1` 采纳后 M 档 prompt 45.3 -> 35.2 s、L 档 215.1 -> 167.1 s（**-21% / -22.3%**），
> decode 占墙钟因此升到 **M 12%**（4.7 s / 40.0 s）。排序结论（prefill 为主）**不变且更强**。
> 且本件"prefill 是 CPU/GPU 双满的地板"这一隐含前提**已被推翻**（`W792 §4.3`：hc read 只跑到 f32 峰值的 26%、带宽 5%）。
> 现行队列以 `W776 §12.5` 为准。

### 2.1 新 decode 基线（`--resident-experts` 已去掉）

`STRATA_DECODE_TIMING=1` + `STRATA_VERIFY_PROFILE=1`，每档 4 runs（L 档 1 run），稳态 94-100 窗口，四轮极差 <1.7%。

| 组 | M (21.8K) | S (2.8K) | L (99K) |
|---|---|---|---|
| 专家流（VRAM hits / waitB / waitCPU） | 10.08 (21.9%) | 10.58 (22.3%) | 8.24 (20.7%) |
| HC 投影（hc0/hc1 的 norm+down+up） | 7.42 (16.1%) | 7.78 (16.4%) | 5.91 (14.8%) |
| 量化 + dense GEMV | 6.13 (13.3%) | 6.40 (13.5%) | 4.88 (12.2%) |
| router + plan + bell | 3.74 (8.1%) | 3.72 (7.9%) | 3.70 (9.3%) |
| 注意力（attention + scores+topk） | 3.31 (7.2%) | 2.88 (6.1%) | **4.30 (10.8%)** |
| out-proj | 3.20 (6.9%) | 3.34 (7.1%) | 2.51 (6.3%) |
| z（GDN 门控投影） | 2.63 (5.7%) | 2.79 (5.9%) | 1.99 (5.0%) |
| shared + quant | 2.66 (5.8%) | 2.75 (5.8%) | 2.21 (5.5%) |
| head | 1.94 (4.2%) | 2.02 (4.3%) | 1.53 (3.8%) |
| ab + rec | 1.72 (3.7%) | 1.77 (3.7%) | 1.53 (3.8%) |
| 其余（kv/gate/copy/pcie/waitA/gap） | 3.28 (7.1%) | 3.31 (7.0%) | 3.10 (7.8%) |
| **合计** | **46.13**（四次运行中位 46.35，见注） | **47.35** | **39.90** |

自校验（**AUDIT7 P2-2 更正，二次修正**）：M 列「合计」已由 46.35 改为 **46.13**（单次运行），使**分项、合计、百分比、每 token 四者同源**；按印刷值求和为 **46.11 / 47.34 / 39.90**，与合计差 **-0.02 / -0.01 / 0.00**，与本节声称的自校验一致。**46.35 是四次运行（46.13/46.44/46.90/46.26）的中位数**，作为 `P91` 的基线值另行记录，不再混进本表。L 列原写 3.01 时差 0.09，已补为 3.10。**另需注意：百分比列的分母是 46.1（单次），不是 46.35** —— 验证：`10.08/46.1 = 21.9%`、`7.42/46.1 = 16.1%`、`6.13/46.1 = 13.3%` 全部对上。=> 下次同类表必须**同一来源**：分项、合计、百分比三者取同一次运行。
每 token：13.85 / 13.76 / 18.82 ms（L 档更慢是因为每窗口只摊到 2.12 个 token，固定开销占比高）。

**与旧表（`P87`）的关系（`AUDIT7 P1-1` 更正了理由，结论不变）**：旧表 74.76 ms 是在 `--resident-experts` 开着时测的，真正的缺陷是**口径混用** —— 分项取自 `decode GPU stages`（total **55.65**，GPU-only），而 74.76 是**墙钟**；用 55.65 的分项去解释 74.76 的总数，每一项占比都会系统性偏低。
原先「旧表不自洽，差 11.31 ms」的说法**是错的**：那 11.31 ms 就在同一行末尾的 `adapt wait 10.69 + join 0.61`，加上即 74.75。把 21 条 `decode timing` 行逐条求残差，全部在 -0.01 到 +0.02 之间。=> 旧表仍然作废（口径不对），但**不是因为它算错了**。

### 2.2 prefill 期间 GPU 满载（推翻了 `W784` 的结论）

`rocm-smi --showuse` 每 1 s 采样，跑一个 M 档请求（prompt 44.4 s + decode 5.1 s，共 55 s）：

```
samples 49  |  histogram: 100 x42, 99 x4, 98 x1, 68 x1, 0 x1
median 100  p10 99  p90 100  max 100  zero_share 2%
```

`W784` §2 记的「105K 请求预填 229.6 s **GPU util = 0%**，22 核 CPU 满载」**是错的**——那是 netdata 的采样口径问题（跨进程 diskstats / 采样间隔错过脉冲）。实测 prefill 期间 GPU 就是满载。

**这条纠错的意义**：只要"prefill 时 GPU 空闲"这个假设成立，"把专家算力搬到 GPU"就是最大机会。现在这个假设被推翻，那条路不存在。

**必须区分的边界（否则又是一次"用错条件推翻对结论"）**：

| 状态 | 判据 | prefill 性质 |
|---|---|---|
| **热态**（page cache 已含全部专家） | 日志 `file tier 0.0 GiB`、`78.9 GiB available for the page cache` | **GPU + CPU 同时满载，算力 bound**（本文实测） |
| **冷态**（page cache 未热，专家要从磁盘读） | 日志 `file tier` 非 0、`read from the drive` 非 0 | CPU 等磁盘，I/O bound |

本轮 49 样本测的是**热态**（生产稳态：`--resident-experts` 去掉后 page cache 涨到 78.9 GiB，能覆盖 55.4 GiB 专家集）。
所以本文的"prefill 是算力地板"只对**稳态**成立；**冷启动第一个请求**仍受磁盘约束，那条路与本方案无关（也不值得优化，一天只发生一次）。
`2026-10-22` 那次"GPU 0%"的另一半疑点也在这里：当时确实有 3,489.8 MB 磁盘读，但后来证伪为 `docker run` 拉镜像层被整机 diskstats 计入。两次都指向同一个结论：**那个 0% 不能作为"GPU 空转"的证据**。

### 2.3 prefill 是算力硬地板（日志原话）

```
prefill plan: chunk 8192, ring 96 kept: file set 0.3 GiB fits the page cache 78.9 GiB
             -> about 0.0 GB read from the drive per 32768-token prompt
prefill plan inputs: 55.4 GiB experts, 22.3 GiB in the GPU caches, 36.6 GiB RAM copy
             (1553 lend slots kept), file tier 0.0 GiB; 78.9 GiB available for the page cache;
             PCIe 12.0 GB/s; drive 0.45 GB/s
```

三件事同时成立于一条日志：**磁盘读取 0**、**全部专家在 GPU(22.3) 或 RAM(36.6)**、**PCIe 12 GB/s 未饱和**。配合 §2.2 的 GPU 满载与历史记录的 CPU 满载 => prefill 是纯算力 bound，不是 I/O bound。

=> prefill 侧唯一还能动的是「提高 CPU 那段专家计算的效率」（AVX-2，无 AVX-512）或「让更多专家进 GPU」（加槽三条路已全关）。**这两条都到地板了。**

---

## 3 真正的最大杠杆：对话复用（`Q6` 从"外部"改成第一优先）

### 3.1 实测（0.2.4 / 0.1.49.2，同一前缀连发三轮，只改结尾三个字）

| prompt | 轮 | reused | prompt_ms | conversation_cache |
|---|---|---|---|---|
| **7,343** | 1 / 2 / 3 | **0 / 0 / 0** | 15,327 / 15,021 / 15,219 | parked 2->4, bytes 994->1,649 MB |
| **19,469** | 1 | 0 | 40,140 | parked 4 |
| 19,469 | 2 | **16,384** | **7,761** | bytes 1,697 MB |
| 19,469 | 3 | 16,384 | 7,792 | bytes 2,084 MB |

分界线精确落在 **8,192（一个 chunk）**：7,343 差 849 token 就完全用不上缓存；19,469 能复用两个 chunk（16,384），但**最后一个不完整 chunk（3,085）仍要重算**。

### 3.2 源码根因（`generate.cpp:9903-9931`）

```cpp
const int64_t done = p0 + T;                                        // 一个 chunk 读完才更新
const bool periodic_checkpoint = o.prompt_cache_every > 0 && done >= pp_next_check;
const bool tail_checkpoint = o.prompt_cache_tail && o.prompt_cache > 0 && o.prompt_cache_every > 0 &&
    !multi_gpu && !pp_tail_saved && pp_total - done > std::max<int64_t>(1, o.short_read) &&
    pp_total - done <= T;
```

- 7,343 的 prompt：`done = 7343 < pp_next_check = 8192` -> `periodic` 假；`pp_total - done = 0` -> `tail` 假。**两个条件全不满足，永不 checkpoint。**
- 19,469：`done` 序列 8192 / 16384 / 19469。16384 触发 `periodic`，然后 `pp_next_check = 24576`；19469 时 `periodic` 假、`tail` 的 `pp_total - done = 0` 也假 => 尾段 3,085 永不 checkpoint。

**即上游把 checkpoint 与 chunk 边界绑死了，代价是所有"不满整 chunk 的尾部"都白读。**

### 3.3 修复（加一个条件，不改任何计算）

```cpp
// NEW: 读完整段 prompt（含最后一个不完整 chunk）也存一次
const bool final_checkpoint = o.prompt_cache > 0 && o.prompt_cache_every > 0 &&
    !multi_gpu && done >= pp_total && done >= 1;
if (periodic_checkpoint || tail_checkpoint || final_checkpoint) { ... }
```

安全性核对：
- `checkpoint_at(L, parts, as_tail)` 的 `as_tail` **只影响淘汰优先级**（`if (!as_tail && L == tail_ckpt_len) tail_ckpt_len = -1;`），不影响 KV 内容，**不改答案**。
- `checkpoint_at` 内有去重：`for (ConvCheckpoint& c : checks) if ((int64_t) c.ids.size() == L) { c.used = ++check_clock; return true; }`，同一长度不会重复存。
- `multi_gpu` 时不动（我们是单卡）。

### 3.4 预期收益（按实测外推）

| 场景 | 现状 | 修复后 | 倍数 |
|---|---|---|---|
| 7,343 对话第 2 轮 | 15.0 s | ~0.5 s（只算新增约 7 token） | **~30x** |
| 19,469 对话第 2 轮 | 7.8 s | ~0.5 s | **~15x** |
| 21,827（M 档）第 2 轮 | 44.4 s（若只复用 16384 则 11 s） | ~0.5 s | **~88x** |
| 2,813（S 档）第 2 轮 | 6.5 s | ~0.3 s | ~20x |

对照：decode 侧全部六项做完、每项 +10%，在 M 档只值 **端到端 1%**。

### 3.5 代价与风险

- 每次 prefill 多存一份 checkpoint：约 **100-300 ms** + **300-500 MB** 缓存（实测 7,343 token 的 cc 约 300-500 MB/份）。
- `--conversation-cache-mib 4096` 能存 8-13 份，多轮长对话按 LRU 淘汰旧份 —— 符合预期，但需要观察 `cc parked` 是否抖动。
- **偏离 upstream**：应本地做，同时把 §3.1 的三轮数字发上游（`#3950` 与 `#3667` 都还开着，且都只挂着机器人提醒）。

---

## 4 队列 v3

### 4.1 排序原则（改了）

旧原则：按 `ms/window` 占比排。
新原则：**按「端到端收益 = 阶段占比 × 该档墙钟占比 × 可动性」排**，并对"可动性"要求给出证据等级。

| 序 | ID | 内容 | 端到端收益 | 证据等级 | 类型 |
|---|---|---|---|---|---|
| **1** | **R1** | 对话复用补 `final_checkpoint`（§3.3） | **M 档第二轮 44 s -> 0.5 s** | 源码条件 + 三轮实测 + 19.5K 对照 | 源码 + 重编 25 min |
| **2** | **R2** | 溢出归因：`qsa_select::block_topk_re` 私有段 **1120 B**、`fused_gr::gr_down_v3` **956 B** —— 但先证"在 dispatch 路径上" | decode 侧 <= 3% | ELF 实测；**沿用 §5 纪律 B 先验证在跑** | 测量 + 源码 |
| 3 | R3 | 【**AUDIT7 P2-4**：本列"端到端 0.2-0.4%"只在单轮成立，多轮下应按 decode 内部占比读，见 §4.1 修正】量化 + dense GEMV 按形状扫（`q8+qkv` 3.83 + `q+q-idx` 2.15 ms，13.3%） | M 档 decode 2-4% -> 端到端 0.2-0.4% | 方法来自 routeK `dense_gemv:787-802` | 源码 + 重编 |
| 4 | R4 | 路由 fp64 治理（`router_top10.cu:220-226` 的 512 次 `exp(double)` + 串行 double 加） | 端到端 0.2-0.3% | 代码明确；`fast_kernel` 已有浮点树实现可参考 | 源码 + 重编 |
| 5 | R5 | HC 投影归因（16.1%，第二大） | 未知 | 内核不溢出（W785 §2.2），机理未明 | 测量 |
| 6 | R6 | 注意力（M 7.2% / L **10.8%**，`scores+topk` 在 L 档 +118%） | L 档 1-2% | 上限低，且改答案 | 源码 + 重编 |
| — | R7 | prefill 侧：`--prefill-pipe` / `STRATA_PREFILL_CPU_SHARE` / `--expert-cache-per-layer` | 均改答案或前提不成立 | 见 §4.2 | — |
| — | R8 | 合规基线（冻结 fixture） | 可比性 | — | 测量 |

### 4.2 为什么 prefill 侧三个参数全部不排队

| 参数 | 为什么不排 |
|---|---|
| `--prefill auto:16384` | `P10` 历史结论「`--prefill` 改答案」，且 §2.3 已证 prefill 是算力地板，加大 chunk 只减 chunk 数不减少总计算 |
| `--prefill-pipe R` | 前提是"读与算未重叠"。§2.3 日志已证 `file tier 0.0 GiB`（磁盘 0 读）、PCIe 未饱和 => 没有 I/O 可重叠 |
| `STRATA_PREFILL_CPU_SHARE` | 语义是"chunk 小于 `stream_all_min` 时把 idle 的 decode CPU 池借给预填"。§2.2 实测 GPU 满载、CPU 满载 => **没有 idle 的池可借** |
| `--expert-cache-per-layer` | decode 实测 miss 已只有 **2.9%**（`CPU experts 0.78 entries` vs `VRAM hits 31.66`），该项收益上限 2.6%；且 `generate.cpp:1551` 有反例「decoded 21% slower with it」 |

### 4.3 专家流这一块正式收口

`W785` 把专家流当"上限 32.2% 的最大一块"，现在拆开看：

| 组成 | M 档 ms | 性质 |
|---|---|---|
| VRAM hits | 8.88 | **显存读带宽地板**（命中后必然要读） |
| waitB | 0.57 | miss 等待（旧基线 6.49，**降 91%**） |
| waitCPU | 0.63 | CPU 算专家（旧基线 4.01，**降 84%**） |

去 `--resident-experts` 已经把 waitB + waitCPU 从 **10.5 ms 压到 1.20 ms**。剩下 8.88 ms 是地板，加槽三条路（`kv-grow` 无 VMM / `expert-cache` 无 VMM / 更小量化等于 2-bit）全关。
=> **专家流从"最大可挖项"改为"已收口"，只有 1.2 ms（2.6%）理论残余。**

---

## 5 审计补漏（`AUDIT6` 之外的 3 条，都是本轮新发现）

| # | 问题 | 性质 |
|---|---|---|
| **P2-7** | `P87` 的 `74.76 ms` 与分项和 `63.45 ms` 差 **11.31 ms（15%）**，从来没人核过 | 表格不自洽。纪律 D 要加一条：**分项和必须等于总数**（本轮新表已自校验到 0.02 ms） |
| **P2-8** | `W784` §2 的「prefill 229.6 s GPU util = 0%」是错的，实测 100% | 用了二手监控（netdata）当一手证据。**凡"资源空闲"结论必须用设备自带计数器（rocm-smi）复核** |
| **P2-9** | `P87` 只测 M 档就当全局基线；L 档的 `scores+topk` 是 M 档的 **2.2 倍**（1.24 -> 2.70 ms）、注意力占比 7.2% -> 10.8% | 单档不能代表全局。**基线必须三档** |
| **P1-6** | `W781` §3 把对话复用判为「外部问题，建议报上游，不适合本机硬改」——**低估了两个数量级**（实测 15-30 倍端到端） | 判"外部"之前必须先算**收益量级**，否则会把最大杠杆丢掉 |

---

## 6 与旧队列的映射

| 旧编号（W785） | 新编号 | 变化 |
|---|---|---|
| Q1 `--kv-grow` | — | 已关（VMM 不可达，三臂 slots 恒 9901） |
| Q1' `--resident-experts`（已落生产） | — | 已完成（三档 decode +10.5~11.8%，prompt 不减） |
| Q2 路由 fp64 | **R4** | 降级（端到端只 0.2-0.3%） |
| Q3 量化 + dense GEMV | **R3** | 降级（端到端 0.2-0.4%） |
| Q4 `native_mmvq` upstream 布局 | — | 并入 R3 一起扫 |
| Q5 注意力三项 | **R6** | 降到末位（M 7.2% / L 10.8%） |
| Q6 8K 复用（原"外部，只报上游"） | **R1** | **升为第一**（15-88 倍端到端） |
| Q7 合规基线 | **R8** | 不变 |
| — | **R2 / R5** | 新增：溢出归因、HC 归因 |

---

## 7 举一反三（五条，进纪律）

1. **排序必须用端到端口径。** `ms/window` 占比是"decode 内部的占比"，不是"用户等待的占比"。本轮之前五版队列全部沿用前者，方向性错误。
2. **"分项和等于总数"是硬校验。** `P87` 差 15% 却通过了三轮审计，因为没人做这个加法。新表三档差 <= 0.02 ms。
3. **"资源空闲"必须用设备自带计数器复核。** netdata 说 GPU 0%，rocm-smi 说 100% —— 前者错。凡涉及"某资源没用上"的结论，一律用 `rocm-smi` / `/proc` 直读。
4. **基线必须三档。** 单档会漏掉随长度变化的结构（L 档 `scores+topk` 翻倍）。
5. **判"外部问题"之前先算收益量级。** 对话复用被我判成"外部"两轮，实际是 15-88 倍。判据不是"能不能改"，是"改的收益是否值得偏离 upstream"。

---

## 8 现状

- 生产：`0.2.4` / `0.1.49.2` / slots 9901 / `--resident-experts` 已去 / env 4 项 / `verify PASS=28 FAIL=0`
- 本轮只做测量与文档，**未改生产配置**（诊断 env 已摘，已复核恢复）
- `R1` 需要：改 1 行 -> 重编镜像 25 min -> 重跑 7.3K / 19.5K / 21.8K 三轮 -> 落生产。**回滚位齐全**（`bak023` 镜像、`strata166-407.bak023` 容器、config 备份）

---

## 9 R1 实施记录（2026-10-25 05:0x 开工）

### 9.1 补丁（`deploy/docker/patch_final_ckpt.py`，fail-closed）

在 `generate.cpp:9906` 之后插入：

```cpp
const char* final_env = std::getenv("STRATA_FINAL_CKPT");
const bool final_checkpoint = (final_env == nullptr || std::atoi(final_env) != 0) &&
    o.prompt_cache > 0 && o.prompt_cache_every > 0 && !multi_gpu && done >= pp_total && done >= 1;
```

并把 `if (periodic_checkpoint || tail_checkpoint)` 改为 `if (periodic_checkpoint || tail_checkpoint || final_checkpoint)`。

**为什么安全**（四条，逐条可核）：
1. 存的是 `checkpoint_at(done, nullptr, false)` 的结果 —— 与 chunk 边界存的那份同构（同一个函数、同一份 `ss` 状态）。
2. `as_tail` 传 `false`（因为 `tail_checkpoint && !periodic_checkpoint` 在此分支为假），所以不会把已有 tail 项降级。
3. `checkpoint_at` 内按 `ids.size() == L` 去重：`done == pp_total` 若已等于某个周期点，不会重复存。
4. 不动任何前向计算、不动 KV 内容 => **不改答案**。

**门控**：`STRATA_FINAL_CKPT` 未设或非 0 = 开（按修复对待）；`=0` = 关（A/B 对照臂）。

**fail-closed 断言**（脚本内 6 项 + Dockerfile 指纹块 2 项）：
`final cond == 1`、`if merged == 1`、`old if gone == 0`、`env read == 1`、`periodic kept == 1`、`tail kept == 1`；
Dockerfile 另加 `grep -c 'final_checkpoint' == 2`。

本地副本先试跑（`/tmp/gen_test.cpp`，md5 `ff384ffb9097ea6c…`），diff 落在 `generate.cpp:9905-9918`，只加判定与 `if` 条件。

### 9.2 构建

- 构建上下文 `/home/albus/strata166/build024/`，新增 `patches/patch_final_ckpt.py`（md5 `a08170c5…`）
- 镜像 tag **`strata-gfx906:0.2.4r1`**（旧 `0.2.4` 保留，可整镜像回滚）
- 配方改动：`COPY patches/patch_final_ckpt.py` + 一个 `RUN`（patch + 2 项断言）+ 指纹块加 1 项断言

### 9.3 验收与 A/B 计划

| 步骤 | 判据 |
|---|---|
| 镜像验收 | `--version` = 0.1.49.3 或 0.1.49.2（版本号未改）；二进制 md5 变化；`grep final_checkpoint` 在镜像内为 2 |
| **7.3K 三轮** | 第 2/3 轮 `reused` ≈ 7,343（现状 0）；`prompt_ms` 从 15,000 降到 1,000 以内 |
| **19.5K 三轮** | 第 2/3 轮 `reused` ≈ 19,469（现状 16,384）；`prompt_ms` 从 7,800 降到 1,000 以内 |
| **首次请求负收益** | bench M 4 runs 的 `prompt_tps` 不得低于 486（基线 489.7），即多存一份 checkpoint 的开销 <= 0.8% |
| 正确性 | 同 prompt 逐轮能正常生成、无 `saving a conversation checkpoint failed`；输出不因复用而变化（逻辑等价，见 9.1-4） |
| 回滚 | `STRATA_FINAL_CKPT=0` 一行即退回原行为；再不行切回 `0.2.4` 镜像 |
