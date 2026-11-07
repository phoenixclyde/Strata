# W863 · Prefill：不是没有空间，是"每轮都全量重算"

> 起因：机主指出"有的可以提高 prefill，不是只关注 decode"。查完确认：**decode 那几条线（R30/R32/R35）都是几个百分点，
> 而 prefill 这里是一个数量级的配置缺陷**——多轮对话第二轮的 TTFT 与全新对话一样，增量前缀**完全没有复用**。

---

## 1 先纠正我自己的一个判断

上一轮参数盘点里我写：「`--prompt-cache-every 8192` — 单流短对话很少触发 — **惰性（待证）**」。

**这个判断是错的，而且错得关键。** 它不是"很少触发"，而是**对 2–4K 的对话永远不触发**，
后果是每一轮都付全量 prefill。我把它列成惰性，等于把最大的一块写成了不存在。

---

## 2 实测（零停服，`ci/prefill_probe.py`）

### 2.1 cold prefill 曲线（随机内容，不可能复用）

| prompt tokens | TTFT | CV | 有效吞吐 |
|---:|---:|---:|---:|
| 349 | 843 ms | 71% | 414 tok/s |
| 646 | 1024 ms | 76% | 631 tok/s |
| 1242 | 1313 ms | 82% | 946 tok/s |
| 2468 | 2006 ms | 88% | 1231 tok/s |
| 4859 | 3756 ms | 93% | 1294 tok/s |
| 9707 | 6915 ms | 96% | 1404 tok/s |

三条读数：
1. **吞吐随长度上升**（414 → 1404 tok/s）⇒ 有约 800 ms 的固定成本，摊薄后才是真实速率。
2. **TTFT 的 CV 是 71–96%**——比 decode 的 3.86–4.36% 差一个数量级。n=2 不足以定量，只能定形。
   这条本身是个发现：**prefill 的延迟极不稳定**，任何 prefill A/B 都要 n≥6 起步。
3. 9707 tokens 要 **6.9 秒**。贴长文档的体验就是这个数。

> 与 W853（10-xx）的账对比：那时 2323 tokens 的 prefill wall 是 3883 ms，我现在测 2468 tokens 是 2006 ms，
> **快 1.9×**。原因是 W853 指出的「`wait copy` 让 GPU 空转」在当前版本已被 `STRATA_PREFILL_ISSUER`
> 解决（`prefill.cpp:3456` 的注释就是在讲这件事，默认开）。**所以 W853 那张分相位账已经过期，不能直接拿来定靶心。**

### 2.2 缓存：精确匹配有效，增量匹配完全无效

| 场景 | prompt tokens | TTFT | 相对 |
|---|---:|---:|---:|
| 同一 prompt 第 1 次（cold） | 1915 | **3685 ms** | 100% |
| 同一 prompt 第 2–5 次 | 1915 | **252 ms** | **6.8%**（14.6×） |
| **第 2 轮 = P1 + 400 新 token** | 2903 | **4418 ms** | — |
| 对照：全新 2903 token | 2903 | **4411 ms** | 100% |

**增量前缀付出 100.2% 的全新成本。** 也就是说：

- 同一段 prompt 再问一次 → 快 14.6 倍（这是 `--prompt-cache 6` 的精确匹配在起作用）
- **对话往下接一句 → 一点没省，全部重算**

而"对话往下接"正是单流多轮的真实形态。

---

## 3 根因（源码核实，不是推测）

两个检查点机制，对 2–4K 的对话**都失效**：

```cpp
// generate.cpp:11071
const bool periodic_checkpoint = o.prompt_cache_every > 0 && done >= pp_next_check && !sp.layer_major_mid();
```

`--prompt-cache-every 8192` ⇒ `pp_next_check` 从 8192 起。2412 或 2903 个 token 的 prompt
**永远到不了 8192** ⇒ 一个周期性检查点都不会存。

```cpp
// generate.cpp:11074  tail_checkpoint 的四个前提
o.prompt_cache_tail && o.prompt_cache > 0 && o.prompt_cache_every > 0 &&
pp_total - done > std::max<int64_t>(1, o.short_read) &&
pp_total - done <= T          // T = 本 chunk 的真实大小
```

- 生产**没有开** `--prompt-cache-tail`（第一条就不满足）；
- 即使开了：`--prefill auto` 的 chunk 是 8192，2412 tokens 只占**一个** chunk，
  处理完时 `pp_total - done = 0`，不满足 `> short_read` ⇒ **仍然不触发**。

所以：**当前配置下，2–4K 的对话没有任何检查点可用，每轮必然全量 prefill。**
`--prompt-cache 6`（默认）只负责"同一 prompt 精确命中"，管不了"续写"。

---

## 4 修法（纯参数，不改一行代码）

| 方案 | 改动 | 机制 | 代价 |
|---|---|---|---|
| **A（推荐）** | `--prompt-cache-every 8192 → 1024` | `periodic_checkpoint` 在 done=1024、2048… 触发，第二轮只重算最后 <1024 tokens | 每个检查点要拷一份 KV 状态；`--prompt-cache 6` 够放 |
| B | 加 `--prompt-cache-tail` | 只在"最后一个 chunk 起点"补一个检查点 | 单独用**对小 prompt 无效**（§3），必须同时把 `--prefill` chunk 调小 |
| C | A + B | 双保险 | 两者都改，收益可能重叠 |

**预期收益**（按 §2 的数据推算）：

- 现在：每轮 2903 tokens × (4418 ms / 2903) ≈ **4.4 s**
- A 之后：只重算 ≤1024 tokens ⇒ 约 **1.4–1.7 s**
- ⇒ **每轮省约 2.7–3.0 s，约 2.6–3.1×**，而且这是**每一轮**都在收的钱

对比这几轮在 decode 上的成果（R 表 +4%、dp4a 判否、R×S 无交互），这条的量级完全不同。

---

## 5 验证设计（需 1 次重启，约 5 分钟停服）

1. 基线：现在跑一遍 `prefill_probe.py` 的 Q4（已有：4418 ms）；
2. 改 config 的 args：`--prompt-cache-every 8192 → 1024`，重启（≈250 s）；
3. 再跑 Q4：看 `turn 2` 的 TTFT 是否从 4418 ms 掉到 ~1500 ms；
4. 对照：Q1 的 cold 曲线不应变化（证明改动只影响复用，不影响算力）；
5. 门：`strata-ci check` + `/health`；不通过就回滚 args（一次重启，5 分钟）。

**判据**：turn 2 / 全新 的比值从 100% 降到 <40%（即复用 ≥60%）。
低于这个数就是没修好，回滚。

---

## 6 顺带把 prefill 的天花板算清

用 §2 的 cold 曲线估算力利用率（每 token 激活约 7.5B 参数 ⇒ 15 GFLOP）：

| tokens | 时间 | 有效算力 | 占 MI50 FP16 峰值 26.6 TFLOPS |
|---:|---:|---:|---:|
| 2468 | 2006 ms | 18.5 TFLOPS | **~70%** |
| 4859 | 3756 ms | 19.4 TFLOPS | **~73%** |

⇒ **prefill 的算力利用率已经在 70% 量级**，kernel 层面最多再挖 1.2–1.4×，而且那要动 GEMM。
**所以 prefill 的钱不在 kernel，在缓存命中率**——这与 decode 的结论正好相反（decode 是带宽/算术问题）。

---

## 7 由此产生的两条纪律

1. **"某个参数很少触发"这个判断必须用数据说，不能用场景推测。** 我上一轮把 `--prompt-cache-every`
   判成惰性，是拿"单流短对话"推的；实测它是"永不触发"，后果是每轮全量重算。这是本项目第 8 次同类错误：
   **用推测代替测量**。
2. **TTFT 的噪声（CV 71–96%）比 decode 差一个数量级**，所以 prefill 的任何 A/B，n 从 6 起，
   并且必须报 CV——否则 2 s 的差异可以是噪声。

---

## 8 状态

| 项 | 状态 |
|---|---|
| cold prefill 曲线（349–9707 tokens） | **DONE**：414–1404 tok/s，固定成本约 800 ms |
| 精确匹配复用 | **有效**：3685 → 252 ms（14.6×） |
| **增量（续写）复用** | **完全失效**：100.2% 全量重算 ← 本轮核心发现 |
| 根因 | **源码核实**：`prompt-cache-every 8192` 与 `prefill auto chunk 8192` 让两个检查点机制都够不着 |
| 修法 | **纯参数**：`--prompt-cache-every 1024`（待批，1 次重启） |
| 预期 | 每轮 TTFT **4.4 s → ~1.5 s（2.6–3.1×）** |
| prefill 算力利用率 | **约 70%** ⇒ kernel 层面只剩 1.2–1.4× |

---

> ## ⚠️ 本节结论已被 §10 推翻（保留原文作为记录）
>
> §9 写「引擎只做整段精确匹配，缺前缀缓存能力」——**错的**。那是我探针的构造缺陷：
> 把第 2 轮写成 `P1 + 新词`，**跳过了模型自己的回复**，于是第 2413 个 token 就分叉，0 复用是
> "对错误问题的正确答案"。真实多轮（`[user P1][assistant reply][user P2]`）实测 **80% 复用**，
> 见 §10。**C4 上游提案已撤回**——引擎不缺这个能力。

## 9 R40 实测结果：参数改不动它（2026-11-01 20:1x，已回滚）

按 §5 的设计改了 `--prompt-cache-every 8192 → 1024` 并重启（healthy 291 s）。

### 9.1 改动确实生效了

引擎进程的真实命令行里是 `--prompt-cache-every 1024`（从 `/proc/<pid>/cmdline` 读的），
不是"以为改了"。顺带确认 `--pack /data/packs/ud-q4_k_xl`——**配置文件叫 `-ud-iq4_xs.json` 是遗留命名**，
实际模型是 ud-q4_k_xl，这一点在报告里要说对。

### 9.2 但它什么都没改变

| | 改动前（基线） | 改动后（1024） |
|---|---:|---:|
| turn2 / 全新 | **99%**（99/100/97，CV 1%） | **100%**（99/101/100，CV 1%） |
| turn2 绝对 | 5784 ms | 6028 ms |

n=3，判据 <40%，两次都远超阈值。**R40 判否。**

### 9.3 日志给出了真正的原因

```
prompt 3066 tokens = 0 reused   + 3066 read in 4747 ms     ← 第一次
prompt 3066 tokens = 3061 reused + 5 read in 225 ms        ← 完全相同的 prompt
prompt 2903 tokens = 0 reused   + 2903 read in 4546 ms     ← P1 + 400 新 token
conversation cache: parked=4 bytes=1083214768 reused_kv_bytes=0
```

两条对照放在一起，结论就唯一了：

- **完全相同的 prompt：复用 3061/3066 = 99.8%，225 ms**（快 21 倍）
- **前缀增长 400 token：0 reused，全量重算**
- 缓存里**确实存着东西**（parked 4 个对话、1.08 GB、`1 checkpoints`/请求），只是**从不还回来**

⇒ 这个引擎的 prompt cache 是**整段精确匹配**，**不是前缀匹配**。
`--prompt-cache-every` 只影响"多久打一个检查点"，管不了"打了之后能不能被前缀命中"。

源码也印证：`generate.cpp:14222` 的恢复循环只遍历 `checks`（已按会话过滤的检查点），
没有与当前 prompt 做前缀比对；`STRATA_SLOT_CKPT_MOVE` 的注释原文就是
**"a second request with the same history"**——设计前提是「历史相同」，不是「历史增长」。

### 9.4 而且 1024 对长 prompt 有害

`periodic_checkpoint` 每 `prompt_cache_every` 个 token 触发一次。1024 意味着
10K 的 prompt 要打 **9 个**检查点，每个都是一次 KV 状态拷贝（`checkpoint_at`），
而这些检查点在"前缀增长"场景下**一个都用不上**。所以它是"纯成本、零收益"。

**已回滚**（`cp ...w863r40.bak → config` + 重启），恢复 `8192`。

### 9.5 这次实验真正买到了什么

不是收益，是**把一条路彻底排除**，并且纠正了我的一个错误定性：

| 之前的说法 | 现在 |
|---|---|
| `--prompt-cache-every` 是"惰性" | **对 <8192 的 prompt 确实惰性，但调小它没用**——瓶颈不在检查点频率，在匹配语义 |
| 改 1024 能让多轮复用 | **不能**。实测 100%，与基线无差别 |
| 引擎有前缀缓存 | **只有整段精确匹配**。多轮对话每一轮都付全量 |

⇒ 真正的修法在**上游代码**，不在我们的参数面。这是一个可以提给上游的明确需求：
**让 `checks` 的恢复支持"检查点是当前 prompt 的前缀"**（幂等、不改数值，只需放宽匹配条件）。

我们这边能做的是把它写进 `UPSTREAM_CONTRIB.md` 的候选，而不是继续在参数上试。

---

## 10 更正：引擎本来就有前缀缓存，80% 复用在真实多轮上成立

### 10.1 我错在哪

§9 的探针把第 2 轮构造成 `P1 + 新词`。真实对话的第 2 轮必须带**模型自己的回复**：

```
[user: P1] [assistant: reply1] [user: P2]
```

parked 对话保存的正是 `P1 + reply1`。少了 reply，第 2 轮从第一个新 token 起就与 parked 分叉，
`conversation_prefix()` 的 `std::equal` 立刻失败 ⇒ 0 复用。**这不是引擎的限制，是我的测试不真实。**

而且源码里这个能力一直都在（不是"缺失"）：

```cpp
int64_t conversation_prefix(const ConversationCheckpoint& c, const vector<Token>& prompt, ...) {
    if (n == 0 || n >= prompt.size() || !std::equal(c.ids.begin(), c.ids.end(), prompt.begin())) return 0;
    return (int64_t) n;         // 检查点是 prompt 的前缀，就返回它有多长
}
```

`ConversationCache::best()` 遍历所有 parked 对话与检查点，取**最长前缀**；
`borrows()` 决定"借中间检查点"还是"整段接管"。

### 10.2 真实多轮的实测（`ci/prefill_multiturn.py`，n=3）

| 轮 | turn1 | **turn2** | 对照：同等长度单轮 | ratio |
|---|---:|---:|---:|---:|
| 1 | 4299 ms | **2214 ms** | 4351 ms | **51%** |
| 2 | 3655 ms | **2207 ms** | 4306 ms | **51%** |
| 3 | 3514 ms | **2044 ms** | 4231 ms | **48%** |

日志逐条：

```
prompt 2336 tokens = 1867 reused + 469 read in 1586 ms (295.7 tok/s), 2 checkpoints
prompt 2333 tokens =    0 reused + 2333 read in 3750 ms (622.1 tok/s), 1 checkpoints
```

⇒ **复用 1867/2336 = 80%，TTFT 从 3750 → 1586 ms（2.4×）**。

### 10.3 剩下的钱在"恢复开销"，不在复用率

把 1586 ms 拆开：

| 项 | 值 |
|---|---:|
| 实读 469 tokens，按对照的 622 tok/s | ~754 ms |
| **实测总时** | **1586 ms** |
| **差（恢复 parked KV + 检查点挂载）** | **≈ 830 ms** |

也就是说：**turn2 里超过一半的时间不是算出来的，是把上次的 KV 搬回来花的。**
日志里 park 那次是 `parked 1955 tokens in 163.4 ms`，`snapshot_bytes=260 MB`；
恢复要反向搬同样量级的数据，实测约 0.8 s ⇒ **约 300 MB/s，远低于 PCIe 的能力**。

⇒ **新的靶心：恢复路径**，不是匹配逻辑。三个可查的方向：
1. `STRATA_SLOT_CKPT_MOVE=1`（默认关）—— 注释说它把"拷贝 ~112 MB 主机向量"改成"移动"；
2. snapshot 是否只搬增量（`snapshot_bytes` 260 MB vs 实际复用 1867 tokens 的 KV）；
3. 恢复是否走了 pinned 内存与独立流。

### 10.4 台账更正

| 项 | 原判 | 更正 |
|---|---|---|
| R40（改 `prompt-cache-every`） | 判否 | **判否仍成立**——它确实无效，但原因不是"缺能力"，而是**不在关键路径** |
| R41（向上游提前缀匹配） | OPEN，准备提 | **撤回**。能力已存在，提上去是报一个不存在的 bug |
| C4（`UPSTREAM_CONTRIB.md`） | 列为候选 | **撤回**，改为记录"我们的探针构造错误"这一教训 |
| 新开 R42 | — | **parked KV 的恢复开销 ~830 ms（占 turn2 的 52%）** |

---

## 11 R42 归因：恢复慢不是 pinned 问题，是页表粒度（2026-11-01 21:1x，零停服）

### 11.1 三条 env 路径全部堵死（源码核实，不是试出来的）

| env | 结论 | 依据 |
|---|---|---|
| `STRATA_CKPT_ASYNC` | **HIP 上不可用** | `conversation_state.cpp`：`#if defined(STRATA_USE_HIP) \|\| defined(STRATA_HIP_GFX906) … return false;` |
| `STRATA_CKPT_GATHER` | **同上** | 同一处 `#if` |
| `STRATA_CKPT_VRAM_SLOTS` | **分配不出来** | `vram_slot_for` 要求 `fr > n + 3 GiB`；我们有 0.8 GB 空闲 |
| `STRATA_PARK_VRAM_MIB` | **HIP 上完全不参与** | `on_device()` 在 HIP 分支直接 `return false`，注释原文：「no pointer-attribute query in the shims: **the slot takes no part**」 |

也就是说：**gfx906 上会话缓存的加速路径（VRAM 常驻、异步检查点、聚合拷贝）全部被编译掉了**，
只剩同步 PCIe 往返。这解释了 park 163 ms 与 restore ~800 ms 的不对称——**只有 restore 在关键路径上**。

### 11.2 为什么腾 VRAM 不划算

`vram_kv_take` 要求「旁边保留 1.5 GB 空闲」。当前空闲 0.8 GB ⇒ 需腾 **1.2 GB**。
专家缓存 3.13 MB/槽 ⇒ 砍掉 **约 383 槽（5.1%）**。
R26 实测专家读占窗口 24.9%、命中 96.5%；少 5% 的槽会让更多专家走 PCIe，
按 PCIe 比 VRAM 慢一个量级估，decode 全程约慢 **6–8%**，而收益只是多轮第 2 段省 0.83 s。
**代价覆盖整条 decode，收益只落在多轮续写 ⇒ 不做。**

### 11.3 真正对症的那一条：host 侧页粒度

> **【作废 · 2026-11-01 21:2x，见 `W864_RESUME_COST.md`】本小节结论已被探针推翻，不要照它改代码。**
> `ci/probe/pcie_probe.cpp` 实测：256 MiB 主机↔显存 **20.3 ms（13.24 GB/s）**，
> `MADV_HUGEPAGE` 生效到 **AnonHugePages 100%** 时带宽 **13.33 GB/s**，与 4 KiB 页差 **< 1%**。
> 也就是说「4 KB 页 ⇒ 830 ms」在物理上不成立；830 ms 的真身是
> **≈ 390 ms 挂载固定成本（与 KV 大小无关：50 MB 会话 375 ms、260 MB 会话 414 ms）+ ≈ 330 ms 的「复用态每 token 贵 50%」**。
> 下一动作改为「一次 `STRATA_TRACE=1` 重启拿四段拆分」，不是 madvise。
> 下面原文保留，作为「错误推理长什么样」的样本。

`conversation_memory.cpp` 的注释写明 KV pool 是 pinned 的：

> `shmem (pinned complements, the KV pool)`

所以 830 ms **不是** pinned 问题。同一份注释也点出它是 **shmem**，而 shmem 默认页是 **4 KB**：

```
260 MB snapshot ÷ 4 KB = 约 65000 个页表项
```

业内实测（KV offload 工程实践）：把 host KV pool 用 `madvise` 合成 **2 MB 大页**再注册，
「映射条目降到约五百分之一，CPU 页表、IOMMU、设备 DMA 三条翻译路径同时受益」；
同一份材料还指出 NUMA 不绑定会让吞吐退化 8–20%，双向异步独立线程提交再降 14%。

⇒ **下一步是 `madvise(MADV_HUGEPAGE)`（一行，零 VRAM 成本），而不是改匹配逻辑或腾显存。**
判据：`STRATA_PARK_TRACE=1` 下 restore 的毫秒数；目标是 830 → 400 ms 以内。
风险：大页分配失败会静默回落到 4 KB，所以必须同时把**实际页大小**打出来，否则又是一次"改了不知道有没有生效"。

### 11.4 R42 的状态

**归因完成，改法明确，但今天不动生产**：这是改 host 内存分配方式，属于引擎内部，
且需要 `STRATA_PARK_TRACE`（一次重启）才能量到收益。留作下一条待批条目。
