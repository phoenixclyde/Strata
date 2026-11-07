# W797 gfx906 从不继承 `arch_default_env`：20 个上游开关在本卡上默认全关

- 日期：2026-10-25 18:58-19:3x
- 触发：`W776 §12.9` 的队列第 2 项（"规则 P 重扫"，原列 `STRATA_ATTN_DAILY` / `STRATA_ATTN_MERGE_V` / `STRATA_PREFILL_STREAM_MIN`）
- 实际做的是**更大的一件事**：把那三个的外延扩到整张 `arch_default_env` 表，并找到了"能不能开"的**秒级判据**
- 产出：register `P115`-`P118`；生产 env 8 → **10 项**；M 档 **-2.62%**、L 档 **-2.86%**

> **【AUDIT9 更正 2026-10-25 22:5x】开关清单与源码不符（结论不变）：**
> `src/core/arch_defaults.cpp` 的 gfx1151 表实际是 **19 项**（文档 §2 写"16 项"、清单列了 20 项）：
> - 清单里多出的 `PF_GEMM` / `PF_HCDOWN` 属于 **`STRATA_IGPU_PROMPT_SET` 家族**（`igpu_prompt_set_enabled`，另一套机制），
>   **不在 `arch_default_env` 里**；
> - 清单漏掉的 **`ATTN_LANECELL`** 才是表内成员（而它在 gfx906 上 +169%，见 W796 —— 反倒佐证"上游默认!=本卡最优"）。
> ⇒ 正确表述：**gfx1151 表 19 项 + gfx12 表 5 项，对 gfx906 全部不适用**。
> 另：§4.1 的"八个臂全部闭合到 2 ms 以内"应为 **<=4 ms**（E/L：相位 660 vs 实差 664）。

---

## 1 结论先行

| 项 | 结果 |
|---|---|
| **`STRATA_GDN_HEAD=1`** | **采纳**：`gdn recurrence` M **2,416→1,729（-28.4%）** / L **11,042→7,883（-28.6%）**；总量 M -0.84% / L -1.56% |
| **`STRATA_GDN_PP=2`** | **采纳**：`gdn recurrence` M **→1,204（-50.2%）** / L **→6,011（-45.6%）**；总量 **M -2.62% / L -2.86%** |
| `STRATA_GDN_NOY=1` | **否决（无增量）**：rec 与只开 HEAD 时无差别（-29.5% vs -28.4%），总量两档方向相反 |
| `STRATA_GDN_CONVL2=1` | **否决（更慢）**：M +0.96% / L +0.43%，靶相位 `gdn` 一点没降，反而 `gather` +103.8%、`wait copy` +22.2% |
| **位一致性** | parity 单测在 gfx906 上跑通：**PP=0 1.68x / PP=1 1.88x / PP=2 2.41x，三档全部 `FAILURES: 0`（y16 与 state 逐位相等）** |

**最重要的一句**：这一轮真正的收获不是那 2.6%，而是发现**上游 20 个 S23/S25/S26 优化在这张卡上默认全关、从来没人测过**，并且找到了一条把"能不能开"的判定成本从 4 分钟（引擎 A/B）降到 **5 秒（parity 单测）** 的路。

---

## 2 结构性发现：`arch_default_env` 对 gfx906 返回空表

`src/core/arch_defaults.cpp` 的三个出口：

```cpp
if (gfx_arch_is_gfx12(gcn_arch))    { ... 5 项 ... return t; }   // RDNA4
if (!gfx_arch_is_gfx1151(gcn_arch)) return t;                    // <-- gfx906 从这里就空了
const char* off = getenv("STRATA_GFX1151_DEFAULTS");
t = { ... 19 项 ... };                                           // RDNA3.5（prompt 8 + decode 11）
```

gfx906 走第二行 ⇒ **空表**。也就是说上游那套"按架构给默认"的机制，对我们这张卡**一项都没有生效**：

| 侧 | 开关 | 落点相位（M 档占比） |
|---|---|---|
| prompt | `GDN_HEAD` / `GDN_PP` / `GDN_CONVL2` / `GDN_NOY` | `gdn recurrence` 7.4% + `gdn` 11.4% |
| prompt | `CVEC_FUSE` / `PF_PAD` | `gdn out proj` 4.1% / `qsa proj` 5.1% / `hc read` 8.1% |
| prompt | `PF_GEMM` / `PF_HCDOWN` | **不在本表**：属 `STRATA_IGPU_PROMPT_SET` 家族（`igpu_prompt_set_enabled`），另一套机制 |
| prompt | `HCD_EXACT` / `TOPK_REG_MIN_BLOCKS` | 需 hipBLASLt 表（我们没有）/ gfx1201 判据 |
| decode | `Q8_PACKED` / `Q6_PACKED` / `MMVF_ROWS` / **`ATTN_LANECELL`** / `EXPERT_V2` / `TSUM` / `LFUSE` / `GDN_SPLIT` / `QFUSE` / `PLE_BATCH` / `SH_STREAM`（11 项） | decode 整体（当前只占 M 10%） |

**为什么上游这么做，注释是逐字的**（`kernels.cu:2729`）：

> `STRATA_GDN_HEAD=1` (on by default on gfx1151; off with `STRATA_GDN_HEAD=0` or `STRATA_GDN_REC_HEADS`) takes them
> (AMD builds only; **the arch defaults set `STRATA_GDN_HEAD=1` on gfx1151 and leave other cards on the earlier kernels**)

"leave other cards on the earlier kernels" —— 这是**故意的**，不是漏。所以不能假设"漏了就去开"，必须先验证。

---

## 3 从"故意关"到"能开"：5 秒判据

`src/prefill/kernels.cu:1240` 那句是嫌疑点：

```cpp
const int tid = threadIdx.x, lane = tid & 31, wave = tid >> 5;
const int g = lane >> 3, cl = wave * 8 + (lane & 7), col = cb * QCB + cl;
```

`lane = tid & 31` 与 `wave = tid >> 5` 是 **wave32 写法**（gfx1151 是 RDNA3.5）。gfx906 是 wave64，第一反应是"这会算错一半列"。

**但这是错的推断，而判据就在仓库里**：`tests/hip/gdn_rec_head.cpp` 是上游给这个内核写的 parity 单测，
判据逐字是

```cpp
const bool ok = d16 == 0 && dsn == 0;   // y16（下游真正读的）与 state 必须逐位相等
// y (the FP32 scratch) is not part of the contract
```

而它**已经是一个 CMake 目标**（`gfx906_gdn_rec_head`）。在 gfx906 上编好跑：

```
PASS T 7    variant 1 vs 0: y 43008,    y16 0, state 0 values differ
PASS T 100  variant 1 vs 0: y 614400,   y16 0, state 0 values differ
PASS T 2048 variant 1 vs 0: y 12582912, y16 0, state 0 values differ
  T 2048 variant 0: 7.651 ms per call (3.74 us per token)
  T 2048 variant 1: 4.562 ms per call (2.23 us per token)
FAILURES: 0
```

**`y16` 与 `state` 全 0 differ，是 PASS。** 所以 `lane = tid & 31` 那套在 wave64 上**是对的**：
HIP 的 `__shfl_sync(0xffffffff, …)` 按 mask 的 popcount（32）划组，物理 wave 是 64 也不影响——
两个 32 半区各自独立工作，恰好就是软件想要的 `wave = tid>>5` 语义。

### 3.1 PP 三档（同一二进制，只换 env）

单测里 `variant 1` 会再查 `STRATA_GDN_PP`，所以**设了 env 再跑一次就等于免费验证 PP**：

| `STRATA_GDN_PP` | 内核 | T=2048 单 kernel | 加速 | FAILURES |
|---|---|---|---|---|
| 0 | `gdn_rec_quad_kernel` | 4.562 vs 7.651 ms | **1.68x** | 0 |
| 1 | `gdn_rec_quad_pp_kernel` | 4.059 vs 7.610 ms | **1.88x** | 0 |
| **2** | `gdn_rec_quad2c_kernel` | **3.186** vs 7.689 ms | **2.41x** | **0** |

三档全部逐位等价，PP=2 最快。**这直接预演了引擎上的结果**（C 臂 rec -50% > B 臂 -28%，与 2.41x > 1.68x 同序）。

---

## 4 五臂实测（p4 镜像，同会话交错 A B C D E，每臂 restart，丢前 2 请求）

| 臂 | env 增量 | M `GPU timeline` | vs A | L `GPU timeline` | vs A |
|---|---|---|---|---|---|
| **A** 基 | — | 32,567 | — | 153,208 | — |
| **B** | `GDN_HEAD=1` | 32,294 | -0.84% | 150,824 | -1.56% |
| **C** | `+GDN_PP=2` | **31,714** | **-2.62%** | **148,831** | **-2.86%** |
| **D** | `HEAD=1 +GDN_NOY=1` | 32,390 | -0.54% | 149,684 | -2.30% |
| **E** | `GDN_CONVL2=1` | 32,880 | +0.96% | 153,872 | +0.43% |

靶相位 `gdn recurrence`（ms）：

| 臂 | M | vs A | L | vs A |
|---|---|---|---|---|
| A | 2,416 | — | 11,042 | — |
| B | 1,729 | **-28.4%** | 7,883 | **-28.6%** |
| **C** | **1,204** | **-50.2%** | **6,011** | **-45.6%** |
| D | 1,703 | -29.5% | 7,756 | -29.8% |
| E | 2,640 | +9.3% | 11,038 | -0.0% |

### 4.1 完整 21 相位对账（规则 P 第二条：相位差之和 ≈ 总量差）

八个臂的比较**全部闭合到 4 ms 以内**：

| 臂/档 | 已列相位合计 | GPU 实差 |
|---|---|---|
| C / M | -854 ms | **-853** |
| C / L | -4,378 ms | **-4,377** |
| B / M | -273 ms | **-273** |
| B / L | -2,386 ms | **-2,384** |
| D / M | -177 ms | **-177** |
| D / L | -3,525 ms | **-3,524** |
| E / M | +312 ms | **+313** |
| E / L | +660 ms | **+664** |

C 臂 M 档的账（其余项 <8 ms）：

```
gdn recurrence   2416 -> 1204   -1212 ms (-50.2%)   <- 唯一该动的
router+shared     879 -> 1054    +175 ms (+19.9%)   <- 迁移
embed+steps       158 ->  251     +93 ms (+58.9%)   <- 迁移
gdn out proj     1345 -> 1405     +60 ms (+4.5%)    <- 迁移（norm 换了内核）
gdn              3715 -> 3734     +19 ms (+0.5%)
```

**"迁移"这一列是必须说的**：`gdn recurrence` 省下 1,212 ms，但同时有 328 ms 从别的相位标签里涨回来
（`router+shared` +175、`embed+steps` +93、`gdn out proj` +60）。这些标签下不可能是 GDN recurrence 的直接后果
（`router+shared` 是路由+计划+bell，`embed+steps` 是 embedding 与采样），所以它们是**时间轴归属的迁移**：
recurrence 变快后，相邻 kernel 在时间轴上的位置变了，事件区间把差异吸收了进去。
**净收益仍是 -853 ms**，但这条要记下来 —— 规则 P 只能保证"该动的动了"，不能保证"只有它动了"。

---

## 5 采纳 / 否决

### 5.1 采纳（P115 + P116）

| 项 | 值 |
|---|---|
| env（10 项） | 原 8 项 + **`STRATA_GDN_HEAD=1`** + **`STRATA_GDN_PP=2`** |
| 镜像 | `strata-gfx906:0.2.4p4`（**不需要重编** —— 内核早就在二进制里，只是默认没开；`strings` 逐个确认过） |
| 收益 | M -2.62%（-853 ms）、L -2.86%（-4,377 ms） |
| 位一致性 | `gfx906_gdn_rec_head` 单测：PP=0/1/2 三档全 `FAILURES: 0` |
| 质量门 | needle 32k@50% 在 B/C/D 三臂均 FOUND；采纳后 32k 深度 10/50/90% 见 §7 |
| 合规 | `verify_config` **PASS=34 FAIL=0**；`gen_config --live` 无差异 |
| 回滚位 | config `.bak_w797_20261025_192524`（8 项）、register `.bak_w797_20261025_192516` |

### 5.2 否决

- **`GDN_NOY`（P117）**：单测注释直接给了原因 ——
  `y (the FP32 scratch) is not part of the contract: 0.1.39's norm kernel no longer stores the normalized value there`。
  也就是**上游的 variant 0 早就不写它了**，省下来的写流量在 variant 1 上本来就已经没有。实测也印证（D 的 rec 与 B 无差别）。
- **`GDN_CONVL2`（P118）**：靶相位 `gdn` 一点没降（+0.13%），反而 `gather` **+103.8%**、`wait copy` **+22.2%**。
  这与 `P111`（`ATTN_LANECELL` +168%）同类：**换协作方式/做融合在这张卡上不必然更快**。

---

## 6 上网查到的：gfx906 专用手法有现成参考实现

`eslowney/llama.cpp-gfx906`（MI50/MI60/Vega VII 专用 fork）的核心手法，逐条都可对上我们的两个大缺口：

| 手法 | 具体值 | 我们的对应缺口 |
|---|---|---|
| **wave64 布局** | `threadIdx.x` = lane 0..63、`threadIdx.y` = warp；归约 `warp_reduce_max<64>` / `warp_reduce_sum<64>` | 我们的 `qsa_decode_attn` 用 `lane = tid & 31` |
| **寄存器分块** | `BLOCK_SIZE = 8`，一次 LDS 读进寄存器后复用 8 次 ⇒ **LDS 流量降 8x** | `qsa attn` 19%（14.7% dp4a） |
| **LDS padding（32 bank × 4 B）** | `GFX906_KV_PADDING = 48` ⇒ 行宽 176 half（352 B = 11×32，非 2 的幂，打破 bank 周期）；`GFX906_Q_PADDING = 32` ⇒ 160 | 与 `P110` 的 swizzle 同源（都是消 bank 冲突） |
| **launch_bounds** | `__launch_bounds__(nwarps*64, 2)`，nwarps=8 ⇒ 512 线程 | — |
| **原生点积** | `gfx906_dot2_f16()` = `v_dot2_f32_f16` | 与 `P103`（`HIP_PROMPT_F16`）同一块硬件能力 |
| 实测 | prompt **5-11%**（Qwen3-30B-A3B Q4_0, pp512-4096） | — |

**注意**：该 fork 只支持 **D=128**（我们的 `head_dim` = 256），且作者写明"only MI50 actually tested"。
所以**不能直接搬代码，但结构可搬**：BLOCK_SIZE 寄存器分块 + 按 32-bank 算的 padding + wave64 归约，
这三条就是 `P5c`（注意力内核重写）的施工图。

另有一条中文资料给的 gfx906 三条硬约束（与我们的实测一致）：块大小取 64 的倍数（我们 128/256 都是）、
每线程寄存器预算 ≈ 64（`__launch_bounds__(256,4)` ⇒ 65536/(4×256)）、wave64 下二分叉最多一半线程闲置
（`P111` 的 +168% 正是这一条）。

---

## 7 生产复核与累计

> 见 §7.1（复核脚本 `albus/r5/conf797.sh`：needle 32k 三深度 + M×2 + L×1，无仪器）

### 7.1 复核结果（无仪器）

```
32k depth  10%: FOUND  (31,640 prompt tokens, 48 s)
32k depth  50%: FOUND  (31,640 prompt tokens, 46 s)
32k depth  90%: FOUND  (31,641 prompt tokens, 36 s)
3 of 3 found
[M] run1 ptok=21827 reused=0 prompt_ms=31221 prompt_tps=699.1 wall=36.8s
[M] run2 ptok=21827 reused=0 prompt_ms=31594 prompt_tps=690.9 wall=36.3s
[M] n=2 reused0=2 | prompt_tps median=695.0
[L] run1 ptok=99387 reused=0 prompt_ms=144867 prompt_tps=686.1 wall=145.7s
```

| 口径 | 采纳前（P109 后生产） | 采纳后 | 差 |
|---|---|---|---|
| M `prompt_ms` | 32,726 | **31,408**（中位） | **-4.0%** |
| M tok/s | 667.1 | **695.0** | +4.2% |
| M 墙钟 | — | **36.3-36.8 s** | — |
| L `prompt_ms` | 150,245 | **144,867** | **-3.6%** |
| L tok/s | 661.5 | **686.1** | +3.7% |

生产口径比 A/B 的 -2.62%/-2.86% 更好，两个原因：(a)生产是 2-3 个样本取中位、A/B 每臂只有 1 个；
(b)**仪器本身有开销**（`STRATA_PREFILL_TIMING=1` 的 A 臂 M 是 32,567，而同一配置无仪器时是 32,726 —— 这一次反向，
说明仪器开销已被样本噪声淹没，两档不能混算）。

### 7.2 今天的累计（M 档，无仪器，21,827 tokens）

| 阶段 | prompt_ms | tok/s | 墙钟 |
|---|---|---|---|
| 09:00 起点 | 45,286 | 482 | 50.6 s |
| +`HIP_PROMPT_F16`（P103） | 35,209 | 619 | 40.0 s |
| +rocBLAS 表 + max-ilp（P107/P108） | 33,437 | 653 | 39.4 s |
| +attn swizzle（P110） | 33,200 | 657 | 38.8 s |
| +`SELECT_SIMT`（P109 翻案） | 32,726 | 667 | — |
| **+`GDN_HEAD`/`GDN_PP=2`（P115/P116）** | **31,408** | **695** | **36.3 s** |

---

## 8 新规则

**规则 Q（立）**：一个开关"上游没给我们的架构设默认"，有三种原因，**判法各不相同**：

| 原因 | 判据 | 成本 |
|---|---|---|
| (a) 只验证过别的架构（**可用**） | 仓库里有该路径的 **parity 单测**，在目标卡上跑一次 | **5 秒** |
| (b) 依赖特定硬件（**不可用**） | 编译成 `__trap()`（`P5` 的第四类）/ 需要没有的库（`HCD_EXACT` 要 hipBLASLt 表） | grep |
| (c) 真的更差 | 引擎 A/B，逐相位 | 4 分钟/臂 |

**先找单测，再决定要不要跑引擎。** 本轮 `GDN_HEAD` 走(a)（单测 5 秒定案），`GDN_CONVL2` 走(c)（无单测，必须实测，结果更慢）。

**规则 O 补一条实测值**：五个臂里 `embed+steps`（158→178~251 ms）与 `router+shared`（879→1,054）的漂移最大，
它们都是"小相位、紧邻主相位"，做相位归因时**要预期它们会被迁移污染**，不能拿它们当判据。

---

## 9 残余风险（照实写）

1. **相位标签的迁移**：C 臂 M 档 +328 ms 涨在非靶相位上（`router+shared` +175 / `embed+steps` +93 / `gdn out proj` +60）。
   总量对账闭合，但**我们不知道这 328 ms 的物理来源** —— 可能是 timing 归属，也可能是真的 L2 竞争变化。
2. **单测覆盖的是内核，不是端到端**：parity 单测证明 `gdn_recurrence_variant` 的输出逐位等价，
   但 `T=2048` 之外的形状（引擎 chunk = 8192）与真实数据分布未覆盖；质量门只有 needle。
3. **`gdn out proj` 在 C 臂 +4.5%(M)/+4.8%(L)**：norm 换了内核（`gdn_out_norm_loop_kernel` 取代 `gdn_out_norm_kernel`），
   输出布局可能不同于 out projection 的最优访存。**没有单独测**，留作下一轮（若把它补回来，C 的收益还能再多 0.3-0.5%）。
4. **decode 侧 10 个开关仍未测**：`Q8_PACKED` / `Q6_PACKED` / `MMVF_ROWS` / `EXPERT_V2` / `TSUM` / `LFUSE` /
   `GDN_SPLIT` / `QFUSE` / `PLE_BATCH` / `SH_STREAM`。decode 现在只占 M 10%，但 L 档 decode 占比更低，
   而**多轮对话场景下 decode 才是主项** —— 这一批要单独按"多轮"场景排。
