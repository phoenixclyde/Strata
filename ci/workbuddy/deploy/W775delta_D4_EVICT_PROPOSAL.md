# W775delta D4 ---- 上游 feature 提案（草稿，待机主过目；**未发出**）

> 依据全部现取：0.1.42 镜像源码（本会话）、`W775delta_W13_RESULT.md` 实测矩阵、上游 GitHub API（2026-10-11 11:2x）。
> 纪律：**本件只是草稿**；按项目铁律，**发上游前须机主过目**。写通道当前可用（W750 §7）。
> 状态：draft。落款候选见 §4。

---

## 0 一句话

上游引擎的 VRAM 专家缓存**从不淘汰**（0.1.42 源码逐字），而上游**自己的**离线工具 `tools/bench_eviction.py`
显示：在真实生产槽位（9,761）上，**现成的 LRU / LFU-decay 就能把命中率从 0.7086 抬到 0.975~0.980**
（oracle 上界 0.9890）。=> 提议在 `ExpertCache::admit` 里加一个 **opt-in** 淘汰策略（默认关 = 现状）。

> **注意：本提案不是「答案中性」的。** 淘汰会改「哪些专家在 GPU 上算」；引擎自己的文档（`bench/results/2026-09-27-cache-parity`）就说 GPU 与 CPU 舍入不同、答复**可能略异** => 采纳必须配**质量门**（同 `ROUTE_TAIL_SKIP` 那一类）。**且我们没测真机速度。**

## 1 为什么不是重复劳动（已核上游，逐字）

| 面 | 证据 |
|---|---|
| **引擎侧无实现** | `include/strata/core/expert_cache.hpp:143` 逐字 *"it never evicts, because eviction policy is a measured question (`R4.1`'s LFU-decay vs LRU sweep)"*；`src/core/expert_cache.cpp:642` *Same "no eviction" rule*；`:653` *full: no eviction, deliberately* => **无实现、无开关** |
| **上游只有测量工具** | `tools/bench_eviction.py`（17,670 B）已在 0.1.42 镜像内；上游 **PR #1089 (open)** / **#991 (closed)** = 就是这个工具 |
| **上游自认未定** | 注释把淘汰策略定性为 *"a measured question"* => 上游**尚未决定**，也**未实现** |

=> **只有"测量"，没有"实现"**。我们提 feature 不与之重叠。

## 2 我们的读数（gfx906 / MI50 32GB / UD-IQ4_XS / 0.1.42；离线复放，**命中率口径**）

| slots | fill-only（引擎现状） | lru | lfu-decay | oracle（上界） |
|---:|---:|---:|---:|---:|
| **9,761**（生产 `/metrics`） | **0.7086** | 0.9751 | 0.9767 | 0.9890 |
| 64 | 0.0105 | 0.3931 | 0.0481 | 0.4221 |

- trace = 3,838 positions x 48 层 x k=10 = 1,842,240 个 `(layer,expert)` lookups；`--prefill` 用生产的 `expert-profile.bin`（对齐起始驻留）。
- 头部空间 **+23.9~28.0 pp**（生产槽位）；**LRU / LFU-decay 只差 oracle 1.2~1.5 pp**（约占 oracle 空间 95%）。
- 槽位越小越惨：slots=64 时 fill-only 0.0105 vs oracle 0.4221 => 现役表现几乎只是"槽位够不够大"的函数。

**局限（必须随结论一起引）**：**命中率口径，非 wall-clock**；收益还取决于 miss 成本（PCIe / CPU pool 占比，本波未测）；
trace 是**一条文本续写**面，不代表生产对话分布全体；oracle 读未来、不可实现，只作上界。**另：淘汰会改「哪些专家在 GPU 上算」=> 答案可能变**（引擎文档自承 GPU/CPU 舍入不同）---- 本提案**不是答案中性**的。

## 3 发给上游的正文（英文草稿，可直接贴 issue / PR 描述）

> 下面这段就是**对外正文**。发之前请机主过目用词与署名。

**Title**

Engine-side expert-cache eviction policy (LRU / LFU-decay), opt-in; measured headroom on gfx906

**Body**

```
Context
-------
`ExpertCache::admit` never evicts.  `include/strata/core/expert_cache.hpp:143` says: "it never evicts,
because eviction policy is a measured question (R4.1's LFU-decay vs LRU sweep)".  `tools/bench_eviction.py`
is the harness for that measurement, and the policies it defines (fill-only, lru, lfu-decay, oracle) are
exactly the candidates.

Measurement
-----------
On a gfx906 / Radeon Instinct MI50 32GB, UD-IQ4_XS pack, engine 0.1.42, we replayed a `--dump-routing`
trace (3,838 positions x 48 layers x k=10 = 1,842,240 (layer,expert) lookups) through
`tools/bench_eviction.py`, prefilled with the production `expert-profile.bin`:

  slots                     fill-only (today)   lru      lfu-decay   oracle
  9,761  (production)       0.7086              0.9751   0.9767      0.9890
  64                        0.0105              0.3931   0.0481      0.4221

At the production slot count the current policy leaves about 24-28 points of hit rate on the table, and
two policies that already exist in your own tool recover about 95% of the oracle bound.  At small slot
counts the gap is far larger (slots=64: 0.0105 vs 0.4221), i.e. today's behaviour is mostly a function of
"are the slots big enough", not of any policy.

Caveat: these are hit-rate figures from offline replay, not wall-clock; the speed benefit depends on the
miss cost (PCIe / CPU pool share), which we have not measured live yet.  The trace is one text-continuation
workload, not the full production distribution.  Oracle reads the future and is not implementable; it is
only the upper bound.

Note on answers: an eviction policy changes WHICH experts are computed on the GPU (vs read from
RAM/files and computed on the CPU).  The engine already documents that the GPU and the CPU round
differently and that a reply "can differ slightly" (bench/results/2026-09-27-cache-parity).  So this
is NOT answer-neutral by construction; adoption would need a quality gate, the same way the other
answers-can-differ switches are handled.

Ask
---
Would an opt-in eviction policy for the VRAM expert cache be in scope?  Concretely, a
`STRATA_EXPERT_EVICT=lru|lfu-decay` environment switch (default off = today's fill-only), with the policy
implemented to match `tools/bench_eviction.py` exactly so the offline prediction and the live engine stay
comparable.  We are happy to prepare the patch if that helps.
```

### 3.1 复现三件套（供上游复核）

- `trace.bin` 16,211,712 B / `6b5f1e44788fc13fa598d4261d5cbcde`（3,838 positions x 48 层 x k=10 = 1,842,240 个 `(layer,expert)` lookups）
- `bench_eviction.csv` 8,253 B / `44c788847e7a2fac397d16501486a845`（9 档 slots x 4 策略 x 4 window）
- `bench_eviction.out` 5,533 B / `9678d411d78f91d8131cbde8b72b838c`（人读版，含本次实际参数）
- 工具签名（上游自带 docstring 逐字）：`bench_eviction.py TRACE... [--slots 4105,8000] [--per-layer] [--windows 4] [--policies fill-only,lru,lfu-decay,oracle] [--decay-window 65536] [--prefill data/expert-profile.bin] [--n-expert 512] [--csv out.csv]`

## 4 待机主确认（发之前的三个点）

1. **发不发**；以及**发 issue 还是 PR**（PR 须先写实现，成本高；**issue 先问 scope 更稳**，我倾向 issue）。
2. **署名 / 致谢口径**（沿用我方惯例：`phoenixclyde`，并注明 MI50 实测来源）。
3. 是否附上 `bench_eviction.csv` 全表（9 档 x 4 策略）作为附件。

> 备注：本件与 `W750 §0.5.5` 的 D4 行同源；D4 的"读上游"两步（(1) 有无实现 (2) 有无同类 issue/PR）**均已完成**。
