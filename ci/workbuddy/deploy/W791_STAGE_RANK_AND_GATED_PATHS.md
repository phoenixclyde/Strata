# W791 全阶段排名 + 上游 gated 路径核查（R4 关闭、GR_SPLIT 判负）

> 机主令「继续，该上网查一定要上网查」。本轮做三件事：**把 decode 全部阶段项排一次名**（不再只看分组）、
> **去上游查那些"默认关、注释写着待测量"的路径**、**逐条实测或源码判定**。
> 结论先行：**R4（路由 fp64）关闭——生产根本不走那条路；`STRATA_HIP_ROUTER_FAST` 实测无效；`STRATA_GR_SPLIT` 净账不成立。**
> 本轮没有拿到性能收益，但**关掉两条会白跑的方向**，并留下一个可复用资产（gfx906 上的 router bit 一致性证据）。

---

## 1 全阶段排名（S 档 97 窗口，total 46.50 ms）

把 `decode GPU stages` 行里每一个字段拆出来（不再分组），按大小排：

| 项 | ms | 占比 |
|---|---|---|
| **GDN `VRAM hits`（专家权重从显存读）** | **6.84** | **14.7%** |
| GDN `q8+qkv/q-idx gemv` | 3.90 | 8.4% |
| GDN `router+plan+bell` | 2.82 | 6.1% |
| GDN `z`（门控投影） | 2.69 | 5.8% |
| GDN `out-proj` | 2.45 | 5.3% |
| QSA `VRAM hits` | 2.26 | 4.9% |
| QSA `q+q-idx` | 2.19 | 4.7% |
| QSA `attention` | 2.06 | 4.4% |
| GDN `shared+quant` | 2.02 | 4.3% |
| GDN `head` | 1.99 | 4.3% |
| HC `down` 四项合计 | 3.60 | 7.7% |
| HC `up` 四项合计 | 3.50 | 7.5% |
| GDN `ab` / QSA `router` / `scores+topk` / `rec` / `shared+quant` / `copy` / PCIe / 其余 | 各 0.3-1.0 | 合计约 15% |

**两条结构性事实：**

- **专家流（`VRAM hits` 9.10 + `waitB` + `waitCPU`）仍然是第一大类**，但 `waitB`/`waitCPU` 已经很小（0.44/0.49），
  剩下的 9.10 ms 是**真的从显存读专家权重**，不是等待 —— 这块在"专家装不下"的前提下没有配置杠杆（`P32/P96` 已收口）。
- `router+plan+bell` 2.82 + QSA 0.95 = **3.77**，比 HC 的 `up`（3.50）还大，是此前没被单独查过的一块。

## 2 上游检索：三个 gated 路径，两个不适用

用 GitHub API 检索 `Niko1221/Strata`（关键词 `HC_Q8` / `gr_up_fast` / `hyper-connection` / `REQ8`），
读过正文的有：

| 条目 | 内容 | 对我们的判定 |
|---|---|---|
| **#3220（open PR）** | `STRATA_HC_Q8=1` 下每个 prefill chunk 有 **192 次标量 `gr_dequant_q8_0_kernel`**（601 GB/s，且把 `wd` 挤出 L2）；PR 把它向量化（8 int8/lane，**bitwise identical**，pair-fused 3.204->1.646 ms = 1.95x），并把 `STRATA_HC_UPMIX` 的 **WMMA** 路径移植到 gfx1200/1201（1.57-1.63x，-14~-21.8 ms/chunk） | **WMMA 部分不可移植**（gfx906 无 WMMA）；**dequant 向量化可移植且 bitwise**，但我们一个 chunk 只有 3 次（21.8K/8192），量级约 **10 ms/首轮**，不优先 |
| **#2810（open）** | SYCL 上 `HC_Q8=1` 原本无效，修好后 verify window 39.4->36.8 ms（**-7%**），decode +17% | 说明 HC_Q8 这类"表示法"开关在不同后端的量级；我们已实测（`P100`） |
| **#2988（closed）** | #3220 的前身，在 0.2.0-beta tracker reset 时被关 | — |

**我们的源码确认不含 #3220**：`grep dequant_q8_0_vec8_item \| gr_dequant_q8_0_pair_kernel` = **0 命中**。

## 3 `STRATA_HIP_ROUTER_FAST=1`：bit 一致，但**无效**（原因在 dispatch）

### 3.1 先证明了它是对的（这一步有价值）

源码 `router_top10.cu:428` 逐字：

> `the S6 kernel is wave32-shaped and only runs here on request (STRATA_HIP_ROUTER_FAST=1) until it is measured on this card`

也就是上游**明确留着这张卡没测**。所以我先做 bit 一致性验证（不动生产构建树，单独编译 `tests/hip/router_fast.cpp` + `router_top10.cu`）：

| 测试 | 结果 |
|---|---|
| 上游自带 `router_fast`（512 专家 k=10，65,536 行；含 ties / near-ties / NaN / 全等行 / 强制串行） | **0 行差异**；portable 53.73 µs -> fast **16.63 µs（3.2x）**；256 专家 k=8 也 0 差异（34.92 -> 13.77） |
| 我自己写的 `rw.cpp`（我们的真实几何 **512 专家 k=6**，393,216 个输出，比的是**默认路径 vs fast**，因为生产走 `router_top10()`） | ids **0 差异**、weights **位相同**；k=10 与 256/k=8 同样 0 |

### 3.2 但生产无效，而且原因很硬

`STRATA_HIP_ROUTER_FAST=1` 单臂（丢弃 2 请求后 M×3）：

| 指标 | 基线（R0b schedutil） | router-fast 臂 |
|---|---|---|
| total | 45.94 | **47.22**（无改善） |
| `router+plan+bell`（GDN/QSA） | 2.82 / 0.95 | **2.80 / 0.95**（**没动**） |

**根因**：`src/core/layer.cpp:420` 逐字

```cpp
if (native_router_enabled() && g.n_expert == 512 && k == 10) {
    try { native_router_top10(b.logits, b.ids, b.weights, stream); }
} else router_top10(b.logits, 1, (int) g.n_expert, (int) k, b.ids, b.weights, stream);
```

我们的 MoE 是 **512 专家、top-k = 10**，所以**走 `native_router_top10`（`native_router.cu`），根本不经过 `router_top10()`**。
`router_top10.cu` 那套（wave / portable / S6 fast）在我们这里是一条**旁路**。

### 3.3 由此产生的两个更正

1. **`R4`（路由 fp64 治理）关闭**，理由不是"收益小"，而是**前提不成立**：`native_router.cu` 里只有 10 个元素的
   `expf` 与 float 累加（`:308` 逐字 `for (int r = 0; r < 10; ++r) { ex[r] = expf(...); sum += ex[r]; }`），**没有 fp64、
   没有 512 次串行 double**。原先 `R4` 引的 `router_top10.cu:220-226` 那段 fp64 在我们路径上不执行。
2. **`router+plan+bell` 3.77 的归属改了**：既然 router 本体已经很轻，这 3.77 的大头是 **`plan`（按层规划）+ `bell`（同步）**，
   要动它得先量 `plan` 与 `bell` 各自的占比 —— 现在没有这个拆分，所以**不排**。

## 4 `STRATA_GR_SPLIT=1`：上游已实现 K-split down，但净账为负

`fused_gr.cu:2303-2306` 逐字：

> `gfx906, opt-in STRATA_GR_SPLIT=1: the latency-hidden norm/up (STRATA_GR_FAST) with the K-split down (~3% faster per verify window). Its fixed-order finish sums the K slices in another order than the single-token fused_gr_read, so the multi-token read is then no longer bitwise equal to T single-token calls (gr_parity's contract); off by default for that reason.`

这正是我在 `W789` 里规划的「路径 B（K 切分 + reduce）」，**上游已经写好了**，而且它自己说 **~3% per verify window**。
但入口条件是同一行的：

```cpp
if (split_on && a[0].s_down == nullptr) {   // its K-split down reads bf16 rows (not STRATA_HC_REQ8)
```

`a[0].s_down == nullptr` 就是 **`HC_Q8=0`**。而 `P100` 实测 `HC_Q8=0` 整体 **+3.3%（更慢）** 且少 169 槽。
=> **GR_SPLIT 的 +3% 建立在 -3.3% 之上，净账为负，不采用。**

**但它给了一条明确的设计线索**：想让 `down` 变快，方向就是 K 切分；而上游的 K 切分只支持 bf16。
若把 K 切分适配 Q8 行（`s_down != nullptr`），就能同时拿到 HC_Q8 的 -3.2% 和 K-split 的 +3% —— **这是 R5b 的第二种形态**，
比"给 `gr_up_fast_kernel` 加 Q8"（实测余量 14% 的 `up`，收益 -1.0%）更值得做。

## 5 举一反三：规则 I（第三次踩同一类）

这是**第三次**"开关生效、但不在 dispatch 路径上"：

| 次数 | 对象 | 表现 | 判据 |
|---|---|---|---|
| 1 | `gr_up75_kernel` | HIP 下 `up75_on()` 直接 return false（死代码） | `W785` |
| 2 | `prompt_attn_i8v3` | 二进制里 grep=0，TU 只有 6 KB 主机桩 | `W783` |
| 3 | `STRATA_HIP_ROUTER_FAST` | env 生效、kernel 也对（bit 一致 3.2x），但**命令不走这条路** | 本轮 |

**规则 I（新增）**：**env 生效 != 在路径上。** 任何"开了某开关却没变化"的结果，第一步不是怀疑测量，
而是去 `grep` 该函数的调用点、确认上游有没有 `if (X) native_*()` 这类前置分派。
判据：**先拿到该阶段的 ms 变化**；阶段值不动就是没走那条路，别再花第二次重启去复测。

## 6 队列影响

| 项 | 原状态 | 现在 |
|---|---|---|
| **R4 路由 fp64** | 排队（8.1%） | **关闭**：生产走 `native_router_top10`，无 fp64 |
| **R5 `up` Q8** | R5b（-1.0%） | 保留，但**降级**为备选 |
| **R5 down K-split（Q8 化）** | 未排 | **升为首选**：上游已有 bf16 版（+3%），我们只需让它接受 Q8 行 |
| `router+plan+bell` | 未查 | 不排（router 本体已轻；`plan`/`bell` 无拆分数据） |
| `STRATA_HIP_ROUTER_FAST` | 候选 | 关闭（旁路） |
| `STRATA_GR_SPLIT` | 候选 | 关闭（净账负）；其机制转为 R5 的输入 |

## 7 本轮产物与状态

- 自测件：`albus/r4/rw.cpp`（我们的几何下 默认 vs fast 的 bit 对比）、`albus/r4/_build_test.py`（上游 `router_fast` 单编译）
- 原始结果：`/home/albus/strata166/data/arm_routerfast_20261025_145105.txt`
- 生产：`strata166-407` = `strata-gfx906:0.2.4` / `0.1.49.2` / slots 9901 / env 4 项 / governor `schedutil`（臂后已还原）
