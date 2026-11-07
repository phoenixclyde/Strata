# W775delta W26 ---- 专家缓存「生产实际策略」离线复放（零停机）

> 触发：`W26` 第二步（量化"我方负载下 fill-only vs 淘汰策略"的命中率差）。
> **本件把 `#1923`（D4 淘汰策略提案）的前提推翻了一半** -- 因为生产**不是** `fill-only`。
> 全部读数现取、可复现；工具与 profile 均与生产同源。

## 0 结论（先行）

1. **生产实际策略 != `fill-only`**：生产是 **profile 预填（9,761 槽，~8 s）+ `adapt()` 自适应迁移层**（日志逐字 `adaptive swaps exchange them with the GPU cache`）。`admit` 不淘汰，但 `adapt()` 会**换入换出**。
2. **用引擎自带的同一套 `adapt()` 模型复放同一条 trace**：命中率 **0.9564**，而"无迁移"是 **0.7086**，该 trace 的静态 oracle 是 **0.9669**。=> **迁移层已拿到该 trace 上 ~98.9% 的可达头部空间**，且与**生产实测 95.4-98.0%**吻合。
3. 因此 `#1923` 里"现役策略还留 24-28pp 在桌上"的**基线选错了**（那是"无迁移"口径）。**我们主动更正 `#1923`**（§6）。

## 1 为什么 W13 的口径不适用于生产

- `W775delta_W13_RESULT.md` 把 `fill-only 0.7086` 称作"**引擎现役命中率**（因为策略=不淘汰 => fill-only 就是现状）"。
- 该论断只对 **`ExpertCache::admit`** 成立（`expert_cache.hpp:143` 逐字 *"it never evicts"*）；它**漏了同一条启动链里另一个组件**：`--resident-budget-gib` / resident RAM mode 下的 **adaptive tier**。
- 生产日志逐字（`strata-huihui-ud-iq4_xs.log`）：
  - `strata generate: pre-filled 9761 of 9761 slots from the profile in 8.2 s (2881 MB/s); slot 0 verified`
  - `strata generate: resident RAM mode: 33.44 GiB of experts in RAM (page-locked), 9761 in the GPU cache; adaptive swaps exchange them with the GPU cache (no file reads)`

## 2 生产实际策略（源码 + 日志 双证）

`generate.cpp` 默认值（生产未给任何 `--adapt-*` 覆盖 => 全默认）：

| 参数 | 源码位置 | 默认值 |
|---|---|---|
| `adapt_every = 4` | `generate.cpp:577` | 每 4 个 verify window 一轮 |
| `adapt_decay = 0.7f` | `generate.cpp:578` | 每轮把 usage 乘 0.7 |
| `adapt_min_gain = 1.5f` | `generate.cpp:581` | 候选须比被换者高 1.5 才换 |
| `adapt_swaps = 96` | `generate.cpp:607` | 每轮最多 96 次交换 |
| 候选门 `u[e] >= 2.0f` | `generate.cpp:8165` | 未驻留且 decayed usage >= 2.0 才可作候选 |
| 迁移规则 | `generate.cpp:8159-8180` | 每层：候选降序 vs 被换者升序，逐对比较；`cand < vict + min_gain` 即 **break**；全层按 gain 排序取前 `swaps` |
| 门的开关 | `generate.cpp:8087` / `:6661` | `adapt_every > 0 && adapt_swaps > 0 && !all_experts_resident`（生产三条全满足） |

> 即：**生产等价于一个"带保证金与衰减的 LFU 迁移层"**，而不是"只填不换"。

## 3 零停机对照实验（本机跑，未停生产）

工具 `tools/replay_cache_policy.py`（`src142/tools/`，镜像内置），trace = `W13` 的 3,838-position 文本续写（`w13_n1024/trace.bin`，16,211,712 B），profile = 生产同源 `expert-profile.bin`（`ff1bc6544d3f2f0013e3e376632d33a8`），slots = **9,761**（生产 `/metrics` 实读）。

| 配置 | share（cache 服务的 routed 条目占比） | swaps |
|---|---|---|
| `replay_cache_policy` policy every 4 + **`--swaps 0`**（关该模型的迁移）**（AUDIT4：此行模型是 policy+swaps0，非 `bench_eviction` 的 fill-only；两者数值同为 0.7086，别混）** | **0.7086** | 0 |
| **defaults（= 生产同构）** | **0.9564** | 11,601（12.06/window） |
| `--every 1`（更勤） | 0.9556 | 7,990 |
| `--margin 1.0 --mincand 1.0`（更松） | 0.9590 | 19,097 |
| （工具自报）同 trace **静态 oracle**（top-9761 by itself） | 0.9669 | - |

**对照（另一种口径，`bench_eviction.py`，同样带 `--prefill` 生产 profile）**：

| policy | hit-rate |
|---|---|
| `fill-only` | 0.7086 |
| `lru` | 0.9751 |
| `lfu-decay` | 0.9767 |
| `oracle` | 0.9890 |

> 口径差别要点：`bench_eviction` 的 `fill-only` **不建模 `adapt()`**（它只模拟 `admit` 的准入）；`replay_cache_policy` **就是 `adapt()` 的模型**（其自带 docstring 逐字 *"The simulated adaptive tier is generate.cpp's adapt()"*）。**谈生产就必须用后者。**

## 4 建模一致性核对（逐条对源码，非"看起来像"）

| 工具参数 | 默认 | 引擎对应 | 位置 |
|---|---|---|---|
| `--every` | 4 | `adapt_every = 4` | `generate.cpp:577` |
| `--decay` | 0.70 | `adapt_decay = 0.7f` | `:578` |
| `--swaps` | 96 | `adapt_swaps = 96` | `:607` |
| `--margin` | 1.5 | `adapt_min_gain = 1.5f` | `:581` / 比较式 `:8174` |
| `--mincand` | 2.0 | 候选门 `u[e] >= 2.0f` | `:8165` |

**五参数逐条对上** => "生产同构"不是类比，是同一个规则集。

## 5 局限（必须随行）

1. trace 是**一条文本续写**（3,838 positions），**不是多轮生产语料**；与生产实测 95.4-98.0% 的吻合是**旁证**，不是同一 workload 的测量。
2. 复放**只覆盖 decode 路由**（`--dump-routing` 只记 decode 面；生产 `/metrics` 也报 `decode expert cache hit rate`）=> 口径同域，但**不含 prefill**。
3. 窗口切分（工具按"层号不再上升"切窗）与引擎 verify window 边界**未必逐一对齐**；本轮只作同一模型内的横向比较，不作绝对预测。
4. `share` 是**命中率口径**，**不是 wall-clock**（`P54` 已证 tier 非瓶颈、miss 走 RAM 交换无文件读）。

## 6 对 `#1923` 的更正（已发上游）

更正要点（英文正文见 `deploy/W775delta_UPSTREAM_W26_CORRECTION.md`）：

- 我们此前把 `bench_eviction.py` 的 `fill-only 0.7086` 当作"引擎现役"，**并据此主张"还有 24-28pp 可达"**；这是**基线选错**。
- 用引擎自带的 `tools/replay_cache_policy.py`（= `adapt()` 的模型）在同一 trace、同一 profile、同一 9,761 槽下：**0.9564**（静态 oracle 0.9669）=> **迁移层已拿到 ~98.9% 的头部空间**；生产实测 95.4-98.0% 同向。
- **我们撤回**"加一个 opt-in 淘汰策略以拿回 24-28pp"的动机；剩下的可能价值收窄为：**(a)** 在 `--resident-*` 模式**关闭**的机器上（`adapt()` 因 `all_experts_resident` 或模式未启用而不跑）是否仍有空间；**(b)** 调 `adapt_*` 参数本身（本轮 `--every 1` / 更松的门**没有**带来增益）。
- 顺带两条上游小观察：(1) 日志 `strata generate: expert cache N slots, X GiB of VRAM; policy is` **缺了策略文本参数**（打印语句以 `"policy is\n"` 结束，见 `generate.cpp:5008`）；(2) `bench_eviction.py` 把 `fill-only` 描述成 *"the engine's current admission"*，容易被读成"引擎现役命中率"，而生产实际还叠了 `adapt()`。

## 7 产物指纹（本机）

| 件 | 字节 | md5 |
|---|---|---|
| `deploy/tmp/_w26_out/replay_default.out` | - | 见文件 |
| `deploy/tmp/_w26_out/replay_swaps0.out` | - | 见文件 |
| `deploy/tmp/_w26_out/bench_prefill.out` | - | 见文件 |
| 输入 trace | 16,211,712 | `6b5f1e44788fc13fa598d4261d5cbcde` |
| 输入 profile | 196,632 | `ff1bc6544d3f2f0013e3e376632d33a8` |
| 工具 | 17,670 / 5,762 | `bench_eviction.py` / `replay_cache_policy.py`（`src142/tools/`） |

## 8 复现命令

```
python tools/replay_cache_policy.py <trace.bin> <expert-profile.bin> 9761
python tools/replay_cache_policy.py <trace.bin> <expert-profile.bin> 9761 --swaps 0
python tools/bench_eviction.py <trace.bin> --slots 9761 \
       --policies fill-only,lru,lfu-decay,oracle --prefill <expert-profile.bin> --csv out.csv
```
