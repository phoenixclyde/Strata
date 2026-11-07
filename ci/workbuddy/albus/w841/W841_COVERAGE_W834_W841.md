# W841 · W834/W835 之后"源码调优"内容的覆盖审计

> 问题（机主）：`W835` 之后有关源码调优的内容，是否都已在方案里。
> 答案：**不在**。下面第 1 节是机械计数（可复算），第 2 节是逐条落点，第 3 节是今天新查到的、**任何文档里都没有**的上游项。
> 处理：全部并入唯一权威 `deploy/W832_OPT_PLAN_V2.md` 新增的 **§6 源码调优台账**（本件只作审计证据）。

## 1 机械计数：权威方案对 W834 之后的覆盖

`grep -c <关键词> deploy/W832_OPT_PLAN_V2.md`（2026-10-31 17:5x，改前）：

| 关键词 | 命中 | 关键词 | 命中 |
|---|---:|---|---:|
| `W835` | **0** | `roofline` | **0** |
| `W836` | **0** | `LDS` | **0** |
| `W837` | **0** | `DPP` | **0** |
| `W839` | **0** | `dot2` | **0** |
| `死块` / `死代码` | **0 / 0** | `LANECELL` | **0** |
| `arch_defaults` | 1（只在 §4.3 提 NaN） | `UPMIX` | **0** |
| `#4283` | 1 | `GDN_CHUNKED` | **0** |
| `#3073` | **0** | `GRAPH_PRIO` | **0** |
| `#4781` | **0** | `CKPT` | **0** |

⇒ **W835（31 KB，含 §9 上游侦察 / §10 Strata 自身缺口 / §11 四开关负结果）、W836（分支 10 commit）、
W839（28 死块）三份，在权威方案里一个字都没有。** 只有 W835 里被转述进 §4.3 的「gfx1151 十项算 NaN」漏了进来。

## 2 逐条落点（改后）

| 来源 | 内容 | 改前 | 改后位置 |
|---|---|---|---|
| W835 §9.2 | gather vs dense 判据（KI 的 DEAD-ENDS：ALU 已满速，换 dot2 无益） | 缺 | §6.3 纪律 |
| W835 §9.3 | 字节侧才是杠杆：**未量化约 14 ms/窗口（31%）**，与 KI 的 T1 清单重合；T-1 反例「probe GO ≠ serving GO」 | 缺 | §6.2 R4 |
| W835 §9.4 | 同模型 ISA 底账（fp16 4.40× vs bf16）；tiled indexer 1.39×；int8 KV prefill 慢 2.5–2.7× **未核** | 缺 | §6.2 R5/R6 |
| W835 §9.6 | 上游 #3986/#4766 撞车、#3073、#4781、#4616、#4159 | 缺 | §6.4 |
| W835 §9.7 | 取代 §6 的执行顺序（roofline 先） | 缺 | §6.5 队列 |
| W835 §10.2 | 四开关（LANECELL / MERGE_V2 / EXPDEC / TSUM）曾列为"最高价值" | 缺 | §6.6 **已实测负**，入"不再做" |
| W835 §10.3 | 纯实现缺口：`HC_UPMIX`（prefill 融合）、`GDN_CHUNKED`（WY 分块 recurrence）、`GRAPH_PRIO`（HIP 硬关）、CKPT/PARK 异步族 | 缺 | §6.2 R7/R8 |
| W835 §11 | 负结果 + 新纪律「别的架构的开关一律按未知处理，先单项测，禁叠加」 | 缺 | §6.6 |
| W836 §1/§2 | 分支身份（`gfx906/0.2.8-mi50`，10 commit / 11 文件 +243−9）、同步边界（CMakeLists 只比标记不比 md5） | 缺 | §6.7 |
| W836 §9 | 两条方法错误（shallow clone 静默空 / 判据失效时数字反而"干净"） | 缺 | §6.7 |
| W839 §6 | **28 个 `STRATA_USE_HIP` 死块** + 「一次只放一块」纪律 | 缺 | §6.8 |
| W839 §7 | 入口生效的三个判据（`nm` 符号 / 二进制横幅串 / 启动横幅 2+7=9） | 缺 | §6.8 |
| W834 | `--pool-workers` 13 vs 默认（§4.5 已在，AUDIT13 改判 UNRESOLVED） | 在 | 不变 |

## 3 今天新查到的（**任何文档里都没有**，2026-10-31 17:5x，GitHub API 实查）

> 方法：`repo:Niko1221/Strata` 搜 `gfx906`（160 条）+ 定点读 12 个 issue/PR 正文；再回 166 的 0.2.8 树逐条 grep 存在性。
> 这一步之前从没做过——W835 §9.6 只查了 6 条，而实际 gfx906 相关条目 **160** 条。

| # | 标题（截断） | 状态 | 对 gfx906 的意义 | 本树是否存在 | 判词 |
|---|---|---|---|---|---|
| **#3987** | gfx906: opt-in two-stage split for the decode QSA top-k | **open** | 长上下文窗口里 indexer top-k 每窗只占 1–6 个 CTA（MI50 有 60 CU），`STRATA_GFX906_TOPK_SPLIT=1` 把 131K 从 0.210→**0.086 ms（2.4×）**、258K 0.324→0.118（2.7×），**ids 3/3 逐位相同** | **不存在**（grep 0） | **最高价值的 decode 移植项**：正是我们 QSA 13.1% 里的 indexer 相 |
| **#4158** | gfx906 prefill: native MMVQ for small-chunk dense projections（`STRATA_PF_MMVQ`） | **open** | 100–256 token 的 agent 轮次，稠密投影解包 + 小 rocBLAS 是主场；MI50 上 165-token 轮 **1.83→1.57 s（−14%）**，大 chunk 不变 | **不存在** | 与 W804 的「1–3K 是 staging+CPU 的痛点」同源，**第二优先** |
| **#3264**（item 2） | HIP: `quantize_q8_0_scaled` 在 `__HIPCC__` 下是 **1 thread/block 串行 32 元素**，CUDA 走 warp-per-block 归约 | open | 我们树里 **确认是这个分支**（`quantize_act.cu:78` 注释「AMD keeps the thread-a-block kernel」） | **存在** | 需 wave64 版 + 逐位门；先确认它是否在热路径（`quantize_q8_0_scaled` 37 处引用） |
| **#3264**（item 1） | `multi_block_head_ops` / `argmax_rows_wanted` 在 `__HIPCC__` 下**恒 false**（T=5 时 402→35.1 µs，11.45×） | open | 本树确认两函数都 `#if defined(__HIPCC__) return false;` ⇒ 我们走单 block 1024 线程版 | **存在但被门死** | **不能只删门**：快版是 warp-32 kernel（`#if !defined(__HIPCC__)`）⇒ 需 wave64 实现 |
| **#4781** | 0.1.54 prompt rate drop：auto expert cache 太小，`--vram-reserve-mib 1536` 恢复 | open | 20K prompt 1139→1588 tok/s。我们 `--vram-reserve-mib 832` + `--expert-cache auto` | 配置项 | **一次 A/B 就能判**（4 min 载入）；代价是槽位 −≈230 |
| **#3073** | `STRATA_SELECT_SIMT=2` 在 HIP 上才真正生效（=1 是静默回退） | open | gfx1030：119K prompt **−6.5%**；本树 `STRATA_SELECT_SIMT` 有 14 处、我们只用了 `=1` | 存在 | **纯 env，零源码**；先确认 `=2` 在 gfx906 上不被同样的回退吃掉 |
| #4206 | `--prompt-cache-every` 低于 chunk 时是 no-op，追加一轮仍全量重读 | open | **本机未复现**：生产日志 `prompt 67 tokens = 62 reused + 5 read`，8858 新 prompt 才 0 reused | — | 记「已核，不适用」 |
| #3476 | 256 专家 router 的 verify-window 路由，除 gfx906 外全 HIP 都缺 | open | **我们已有**（该快路径本就只给 `STRATA_HIP_GFX906`） | 存在 | 不适用 |
| #3913 | HIP `mlock` host 内存，防 swap 卡住队列 | open | 我们 128 GiB RAM、未见 `no progress 60 s` | — | 低优先，记症状备查 |

## 4 一句话结论

**"源码调优"这件事，方案里此前只有 4 条（都来自 W832 §5.2），而 W834 之后实际积累了 13 条 + 今天新查 6 条。**
缺的不是细节，是**整整一层**：W835 的三节（上游侦察 / Strata 自身缺口 / 负结果）与 W839 的 28 死块清单，
从来没进过队列。已全部并入 `W832_OPT_PLAN_V2.md §6`，并把队列重排为"先配置级、再高价值移植、后 roofline 判定"。
