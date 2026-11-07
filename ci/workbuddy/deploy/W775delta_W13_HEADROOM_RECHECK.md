# W775delta ---- `#1923` 自查：「+24~28pp 命中率空间」是**trace 的**，不是我们生产负载的

日期 2026-10-11 ｜ 全部现场现取 ｜ **0 发车**

## 0 为什么要自查

我们在上游 issue **`#1923`** 里写过（本机 9,761 槽）：`fill-only 0.7086` -> `lru 0.9751 / lfu-decay 0.9767` -> `oracle 0.9890`，
据此说 **"约 24-28 个百分点的命中率留在桌上"**。
**但那个 0.7086 是 `bench_eviction.py` 复放一条 `--dump-routing` trace 得到的，不是我们生产负载的命中率。**
机主此前强调过 `#1729` 的教训（被上游质疑、最后还是自己错）=> **本件先自查，再决定要不要主动更正上游。**

## 1 生产实测（现取，来源 = `strata166-407` 引擎日志）

`strata serve: decode expert cache hit rate: <H>% (<hits> hits / <lookups> lookups)`：

| 场景 | 命中率 | lookups 量级 |
|---|---|---|
| 长跑样本 | **97.1%** | 3,078,696 |
| 长跑样本 | **97.0%** | 2,798,217 |
| 分布尾部（多次） | 95.4% - 98.0% | ---- |
| 短请求样本 | **88.1%** | 207,866 |
| 短请求样本 | **90.1%** | 297,507 |

槽位（同日志）：`resident RAM mode: 33.44 GiB of experts in RAM (page-locked), **9761 in the GPU cache**; adaptive swaps exchange them with the GPU cache (no file reads)`

=> **本机生产的稳态命中率约 95-97%（长跑向 97-98% 收敛），而不是 70.86%。**

## 2 差异从哪来（据实列，不猜因果）

1. **负载不同**：我们的生产是**单用户、提示高度自相似**的负载；W13 的 trace 是**一条文本续写**（`--dump-routing` 车，`--max-new 1024`，3,838 positions）。
2. **缓存状态不同**：生产是 `--expert-profile` **预热 + `--adapt-every` 自适应交换**在跑；`bench_eviction.py` 是**离线固定槽位 + 指定策略**的复放。
3. **口径可能不同**：生产那行是引擎自己的 `decode expert cache hit rate`；`bench_eviction.py` 的 fill-only 是复放器算的。**两者是否同义，本件未逐行核**（见 §4 局限）。
4. **`0.7086` 与 `0.7517` 两个 fill-only 值**在 W13 稿里分别对应 slots=9761 / 10327 ---- 即**同一条 trace、不同槽位**；而生产在 9761 槽上跑到 95%+。

## 3 结论（本机侧）

- **`#1923` 里"本机还有 +24~28pp 空间"的表述是按 trace 口径说的，不能直接推到我方生产负载。**
- 就**我们的负载**而言，**淘汰策略的头部空间远小于 24pp**（生产已 95-97%）---- **除非**生产那 95% 里含有"被 `--adapt-every` 交换救回来"的部分（那部分在『从不淘汰』下确实会丢）。**这一点尚未测**。
- => **`W26`（`C1` 命中率面）的触发条件应改写**：不是"上游采纳 `#1923` 后验收"，而是**先量化"我方生产负载在 fill-only vs 淘汰策略下的命中率差"**（这是唯一能回答"我们到底有没有损失"的实验）。

## 4 待机主裁定：是否主动更正 `#1923`

**建议：是**（主动发一条 qualification，而不是等上游质疑）。理由：与该 issue 已发的三处硬化同源纪律（无提速字样 / 显式写"答案可能变" / 附复现三件套），本次属**第四条**：**"命中率数字的负载代表性"**。
草稿（**未发**，按纪律先给机主过目）：

```text
A clarification on our own numbers (they are trace-scoped, not workload-scoped)
------------------------------------------------------------------------------
In the measurement above the 0.7086 fill-only figure comes from replaying a `--dump-routing` trace
(3,838 positions, one text-continuation prompt) through `tools/bench_eviction.py`.  That is NOT the
hit rate our production workload sees.  On the same card, same slots (9,761), our live engine reports
`decode expert cache hit rate` of 95.4-98.0% on long runs (2.8-3.1M lookups) and 88-90% on short ones.

So the "+24-28 points left on the table" applies to a trace-like, cold-cache workload.  We do not know
yet how much of it survives on a workload that a learned expert profile already covers at ~96%.  The
part that plausibly survives is whatever the engine's adaptive swaps bring back today (its cache has no
eviction to fall back on), and we have not measured that split.

We therefore do not claim a production gain here; the proposal stands as "an opt-in policy is missing
and the offline headroom is real for trace-like traffic".  If you want a number for a specific
workload shape, we can measure the fill-only vs lru delta on that shape and post it.
```

## 5 局限（必须随行）

1. 生产那 95-97% 与 `bench_eviction` 的 fill-only **是否同义未逐行核**（两者的 "hit" 定义可能含 RAM tier）。
2. 生产样本来自**单用户负载**；换负载（多用户 / 长文档检索）数字会变。
3. 本件**没有**跑任何车；结论只到"不许把 trace 数字当生产数字"这一层。

## 6 本机侧的有界分析（0 发车，纯算术 ---- 用我们自己的数）

> **[!] W28/AUDIT4 限定（2026-10-11 16:5x）**：本节第 4 条的依据「`P54` 已证 file/RAM tier 非瓶颈」**已被 W28 判为对冷路径错误**（`P54` 现为 CANDIDATE，见 `W775delta_W28_COLD_PATH_REDESIGN.md` E3）；且本节引用的「95.4-98.0%」是**长跑带**，全日志 `decode expert cache hit rate` 实测 **58/196（29.6%）低于 88%、最低 66.7%**（AUDIT4 现算）。=> 本节结论**仅对 decode 稳态**成立，**不要外推到冷读**。

**问题**：在我方**生产负载**上，还有多少命中率可拿（即淘汰策略值多少）？

**证据（全部本机实测）**：
1. 生产实测命中率 **95.4-98.0%**（长跑 2.8-3.1M lookups 时 **97.0-97.1%**；见 §1）。
2. 命中率的**理论上界 = 100%**，故**我方负载上的剩余空间 <= 2.0~4.6pp**（从 98.0% / 95.4% 起算）。
3. `W13` 的 `oracle 0.9890` **同样是 trace 口径**，**不能**当作我方负载的上界。
4. 我方 miss 的代价：生产日志 `resident RAM mode: ... adaptive swaps exchange them with the GPU cache (**no file reads**)`
   => 命中失败走 **RAM 层**（page-locked 33.44 GiB），**不是文件读**。而 `P54` 已证 file/RAM tier 非瓶颈。

**推论（据实，标注为推论）**：
- 淘汰策略在我方负载上的**上限增益 <= 2.0~4.6pp 命中率**，且该 pp 的**单次代价是"RAM 换入"而非磁盘读** => **速度兑现的期望很小**。
- 与之对照：`W13` 那 24-28pp 的头部空间**之所以大，正是因为那条 trace 是冷缓存 + 路由更分散**。
- **`#1923` 对本机的价值因此应当下调**：它仍是"引擎缺一个 opt-in 策略"的**正确**提议（对 trace 类 / 大 RAM 小 cache / 多用户负载真有用），但**不是我们自己的头条机会**。

**要把它变成测量（而不是推论）需要什么**：一条**生产形态的 `--dump-routing` trace**（多轮、自相似、长会话），再跑 `bench_eviction.py --policies fill-only,lru`。
=> 这正是 `W26` 的**第一步**；在未做之前，**不应**对外声称任何生产增益（已按此发 `#1923` qualification）。

**本节不做的事**：不发车、不改任何生产参数。
