# W775delta W13 -- `replay_cache_policy.py` 评估

> 机主令「按计划推进」。W13 = `W750_MASTER_PLAN.md` §1 / `W713_PLAN.md §6.4 #10` 的零发车项。
> 时间：2026-10-11 04:3x。全部读数现取，来源逐条标注。

## 0 结论（先行）

1. **工具族在位且完整**：0.1.42 镜像 `/src/tools/` **108 项**，其中 expert-cache 工具链 **三件**：
   `replay_cache_policy.py`(141 行) · `bench_eviction.py` · `make_profile.py`（另有 `test_bench_eviction.py`）。
2. **它测的东西与我们现役两条缓存参数不是同一层** -- W13 的原始假设「与 P31/P34 重叠或可叠加」**不成立**：
   - `replay_cache_policy.py` / `bench_eviction.py` 测的是 **expert cache 的淘汰策略**（`(layer, expert)` 对的驻留命中率）；
   - `--conversation-cache-mib`(P31) / `--prompt-cache-every`(P34) 测的是 **KV / 会话级缓存**。
   两者在源码里是不同模块（`src/core/expert_cache.*` vs 会话/前缀缓存），**不存在叠加或冲突**。
3. **但它对口另一个困局 -- W769 的「驻留伪影不可分离」**（`W775` 系列未解项）：
   引擎的 `h`（hit rate）在**运行期不可分**，而这个工具**离线**复放同一 trace 可以给出
   `static oracle` / `fill-only` / `lru` / `lfu-decay` **四条对照曲线**，正是分离"驻留布局」与"策略"的刀。
4. **它不改生产**（纯离线，只读 trace + profile），**零风险**。
5. **但发车前提不是"改参数"，而是"先造输入"**：需要一次 `--dump-routing`（引擎内一次性跑，**这不属于"改参数"**，是一条独立 CLI 路径，也要占生产 GPU）。

## 1 链路（源码级，逐字）

```
(1) 引擎一次性跑：  strata ... --dump-routing TRACE.bin
   └ src/program/generate.cpp:756    "  --dump-routing PATH  write the routed expert ids and weights per layer per position (P0.S8)"
   └ src/program/generate.cpp:1802   else if (a == "--dump-routing") o.dump_routing = next("--dump-routing");
   └ src/program/generate.cpp:5505-5513  fopen(o.dump_routing, "wb")
   └ src/program/generate.cpp:5507   "--dump-routing needs the expert pool; the routed ids reach ..."  (无 pool 则报错)
   └ src/program/generate.cpp:12944  printf("%-24s %s (%lld records of layer, k, ids, weights)\n", "routing dumped", ...)
   记录格式：int32 layer, int32 k, k int32 ids, k float32 weights（见 replay_cache_policy.py docstring）

(2) 造 profile：     python tools/make_profile.py [TRACE ...] [--base ... | --no-base] [--reorder] [--out PATH]
   └ magic "STRP" + version,n_layers,n_expert,slots,n_ranked + n_ranked*(layer,expert)
   └ 读方：src/core/expert_cache.cpp:86  memcmp(magic,"STRP",4)；:198 fwrite("STRP"...)

(3) 离线复放：       python tools/replay_cache_policy.py TRACE.bin PROFILE.bin SLOTS [--every 4 --decay 0.7 --swaps 96 --margin 1.5 --mincand 2.0]
   └ 模拟 generate.cpp 的 adapt()：usage += 1/entry、每 `every` 窗口一轮、每层 best-non-resident(>=mincand) 对 worst-resident(需 margin)、全层取 best `swaps`、usage *= decay
   └ 输出四项：windows / static oracle / profile-only-no-adaptation / policy-share

(4) 同族更强：       python tools/bench_eviction.py TRACE... [--slots 4105,8000] [--per-layer] [--windows 4]
                                          [--policies fill-only,lru,lfu-decay,oracle] [--decay-window 65536] [--prefill ...] [--n-expert 512]
   └ **四策略对拍**：fill-only（引擎现状基线）/ lru / lfu-decay / **oracle（Belady MIN，上界）**
   └ 带 `--per-layer`（R4.2g 分层池）与 CSV 导出
```

## 2 关键源码事实（逐字）

**(1) 引擎当前策略 = 「从不淘汰」**（`src/core/expert_cache.cpp:142-143`）：

> `/// Claims the next free slot for (layer, expert). Returns the slot, or kNotResident when the cache is full - **it never evicts**, because eviction policy is a measured question (R4.1's LFU-decay vs LRU ...)`

=> 这解释了 **P33（pin）** 的处境，也解释 W769 的困局：**现役 `h` 是"只填不换"的命中率**，任何自适应/淘汰策略的收益在这个基线之上**根本没被测量过**。

**(2) 上游自己给了同卡命中率实测**（`include/strata/core/expert_cache.hpp:11`）：

> `//   * h_expert at 4,105 slots, **ten-fold leave-one-out: 0.6447 [0.6110, 0.6750]** (tools/routing_kfold.py).`

=> 同族还有一个我们**没在台账里**的工具：`tools/routing_kfold.py`（k-fold 交叉验证命中率）。

**(3) profile 覆盖曲线有 25pp 的自我打脸**（`tools/make_profile.py` docstring，逐字）：

> `... the coverage curve in src/program/generate.cpp carries the measured hit rates that say how far off that goes (**94.9% claimed against 69.2% measured** at 5,805 pairs held, on the IQ3_S 4-way rig).`

=> **上游自己承认"声明覆盖率 94.9% vs 实测 69.2%"** -- 这正是我们 W769 想找的"驻留伪影"来源的**官方出处**。

**(4) 一个必踩的坑**（`make_profile.py` docstring，逐字）：

> `WATCH THE BASE: take() skips a pair it has already ranked, and the shipped base ranks all 24,576, so a plain --base run cannot be moved by any trace - the output is the base again. --reorder (traces first) or --no-base is what makes a trace decide the top.`

=> **用 `--base` 跑，trace 等于没跑**。要让它生效必须 `--reorder` 或 `--no-base`。

## 3 我们生产面的现状（现取）

`/metrics`（2026-10-11 04:3x，`strata166-407` @0.1.42）：

| 键 | 值 |
|---|---|
| `engine.expert_slots` | **9761** |
| `engine.expert_cache_mib` | **22516** |
| `engine.expert_slots_primary` | 9761 |
| `engine.expert_cache_primary_mib` | 22516 |
| `engine.arena_mib` | 34245 |
| `engine.vram_free_mib` | 574 |
| `engine.conversation_cache_mib` | 4096 |
| `engine.conversation_cache_min_tokens` | 0 |

**算术**：全表 = 48 层 x 512 专家 = **24,576** 对；现驻留 **9,761** => **39.7%** 的静态覆盖面。
上游同卡口径（4,105 slots => 0.6447）是**另一台机器**（IQ3_S），**不可照搬**（我们 pack = UD-IQ4_XS）。

## 4 判定：W13 该怎么落

| 问题 | 判定 |
|---|---|
| 与 P31/P34 重叠吗？ | **不重叠**（不同模块：expert cache vs 会话/KV 缓存）。原假设**证伪** |
| 可叠加进生产参数面吗？ | **不能直接叠加** -- 它不是参数，是**离线测量工具**；且引擎**当前策略是不淘汰**，没有"策略开关"可拨 |
| 那它的价值在哪？ | **在诊断，不在调参**：(1) 分离 W769 的「驻留伪影」；(2) 给 P33（pin）一个**离线可证的**命中率上限；(3) 验证 `--expert-cache auto` 的 9,761 是否已接近 oracle |
| 发车成本 | **零"改参数"**，但需**一次 `--dump-routing` 跑**（占生产 GPU；含 `--dump-routing` 属**独立 CLI 路径**，非参数变更） |
| 风险 | **零**（不写 config、不改引擎行为） |

**建议动作**（待机主批准才跑）：
1. 起一个 **dump-only 车**：停生产 -> 引擎加 `--dump-routing /data/w13_trace.bin` 跑**一条有代表性的长 prompt**（>=8K，覆盖多主题切换）-> 停引擎。
2. 本地跑 `bench_eviction.py --slots 9761 --policies fill-only,lru,lfu-decay,oracle`。
3. 读四策略的命中率 -> **`oracle - fill-only` 的差 = 现役策略的天花板**；若差 < 2pp，则**P33/P41/P46 整族可以提前判死**（省掉 W6/W4 的多次发车）。

=> **这是 W13 最大的价值**：它可能用**一次零风险离线跑**，直接给出 W6/W4/P33 那族的天花板。

## 5 局限（必须随结论一起引）

- **未实测**：本报告只做**源码 + 在位性 + 输入链路**的核验，**没有造 trace、没有跑复放**（那需要停生产，属发车范畴，须机主批）。
- `expert_slots=9761` 是**引擎运行时**值；离线复放要**手动指定**同值对齐。
- 上游那个 `0.6447 [0.6110, 0.6750]` 是 **IQ3_S 4-way** 机器，**不是我们的 pack/机**。
- `make_profile.py` 的 `--base` 陷阱若踩，会得到"trace 无效但看起来正常"的**静默错误结果**。


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `09182c73bb11301839b4e5df8efd6d88`（字节 8120）。
