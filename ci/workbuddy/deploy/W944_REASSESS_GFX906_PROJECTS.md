# W944 · 重新评估：上一轮"MMQ 五门全关"是**取样偏差** —— 漏掉了布局层（weight repack）

> **【AUDIT24 P1 · 2026-11-04】§1 的三个数都错（结论不受影响）**：
> ①「88.6%」是**按 offset 列加权**（权重=层号），而且分母是"down 的字节"，不是"专家字节"；
> ②按 `blob_bytes` × 512 专家重算：Q5_1 占**专家总字节 35%**（27.05 / 77.0 GB），在 down 内部占 **86%**，
> 层数 43/48 = **89.6%**；Q8_0 down 是 5 层（11.2% → **9.5%** 的层字节）、Q5_K 1 层（0.2% → **2.7%**）；
> ③「60.5 GB blob」应为 **77.0 GB**（`native_experts.txt` 头部 77,017,907,200 B）。
> ⇒ "Q5_1 是最重的格式"要改成「**Q5_1 是 down 的唯一主格式、占专家字节 35%**」；
> 端到端预期：本件 §60 的 **−6.3%** 已被 `W945 §6.3` 下调为 **0 ~ −6.3%（未知）** —— 只有 down 占 prefill 13.8% 这个分母不变，**上限不能再当预期用**；判据是单内核 A/B（Δ≥40% 才动生产）。

- 日期：2026-11-04 14:3x–15:0x
- 触发：机主「你不是只看 llama.cpp（更何况你手里还不是最新源码），必须参考 gfx906 专门项目。重新评估上一轮，以及相关的所有工作。」
- 结论先行：**指令层（tile / 内层循环 / dot 指令）确实全关，但那是 MMQ 的一半。另一半是数据布局，我们从没看过。**
  `mxxm-t/mx-llama.cpp`（mixa3607 的新家，基线 upstream `b11553`）在 gfx906 上默认开 **weight repack**，官方表格给的是
  **Q5_1 +84%（单卡）/ +74%（双卡 tensor）prefill**，并且明确写了「Qwen3.8-Flash-Next MoE 带 43 个 Q5_1 tensor 时 +11% prefill（四卡）」——**那就是我们的模型、我们的 down 格式**。

---

## 1 我们手里到底是什么（本轮补的第一课）

`data/packs/ud-q4_k_xl/native_experts.txt` 解析（48 层 × 512 专家，60.5 GB blob）：

| gate/up | down | 层数 | 字节占比 |
|---|---|---:|---:|
| Q4_K | **Q5_1** | **43** | **88.6%** |
| Q4_K | Q8_0 | 4 | 11.2% |
| Q5_K | Q8_0 | 1 | 0.2% |

⇒ **down 的 88.6% 是 Q5_1**，而 `W927` 只写了"Q5_1/Q8_0"没量化占比；`W942/W943` 判 MMQ 时也没把"格式的布局代价"作为变量。
`mx` 的收益表恰好是**按格式**分的：Q5_1 +84%、Q6_K +69%、Q5_K +55%、Q4_K 只有 +2~5% —— **我们最重的格式正好是它收益最高的那档**。

## 2 三家 gfx906 专门项目，各自的着力点

| 项目 | 基线 | 着力点 | 与本机相关的实测 |
|---|---|---|---|
| **mxxm-t/mx-llama.cpp**（原 mixa3607） | upstream `b11553`（最新） | **权重布局重排** + TP 分片 + gfx906 kernel tuning | **Q5_1 +84%/+74%、Q6_K +69%/+59%、Q5_K +55%/+50%、Q4_K +2%/+5%**；Qwen3.8-Flash-Next MoE（43 个 Q5_1）**+11% prefill**；q8_1 激活复用 **+2.2~2.6%**（bit-exact）；BF16→F32 compute **+18~19%** |
| **milpster/gfx906-llama-cpp** | upstream `7887b88`（9-24） | 内层循环 / tile / fattn | 41% issue ceiling **结构性**：unroll / prefetch / phase-split / scale-free 四家族**全部回归**；LDS-wait 仅 2.2% ⇒ prefetch 无用；occupancy 路线**关闭**（I=128 的 LDS 放不下第二块） |
| **iacopPBK/llama.cpp-gfx906** | **build 7924（很旧）**，已迁 mx | gfx906 专用 kernel 目录 | `#21698` 的 +28~36% 是在**上游 RDNA2 fallback 表**下测的，换到 vega 表后 milpster 复测 **+1.0%（噪声）** |

**判决**：上一轮引用的两条（`W832` 的 ki/MoE GEMM、milpster 的 41%）都在**指令层**，结论没错；但**布局层从未进入视野**，
而布局层恰好是唯一一个"外证在**我们的模型**上给出 +11%"的项。

## 3 逐条重评上一轮

| 条目 | 上轮结论 | 重评 | 依据 |
|---|---|---|---|
| **R61** VALUBusy 67.1% | DONE | **维持**（A 级），但**解释要改**：VALU 忙的 70% 里有相当一部分就是 **per-block scale gather / 行别名解算**，而那正是 repack 要消掉的东西 | 本轮 PMC + mx 的机制说明 |
| **R60** stream-k | DONE_NEG | **维持** | milpster：LDS-wait 2.2%、occupancy 关闭；与本机 67% VALU 一致 |
| **R63** readfirstlane/prefetch | DONE_NEG | **维持** | milpster 四家族全回归 + 本机 `v_readlane` ≤0.4% |
| **R84** dot8 | DONE_NEG（2.05%） | **维持** | milpster：41% 是结构性；mx 也没做 dot8，而是换了布局 —— 两家的选择一致 |
| **"MMQ 五门全关 ⇒ 只剩 attention"** | 上轮结论 | **错误，撤回** | 正确说法：**指令层五门全关；布局层（repack）从未开门**。repack 的预期（down −6.3% 端到端）比 attention（3.4–5.95%）大一倍 |
| R85 的手段排序 | R46 > R64 | **改成 R86(repack) > R46 > R64** | 外证确定性：repack 有 **byte-identical** 记录（Q5_1 单卡输出逐字节相同）⇒ 不需要精度门，风险远低于改 attention 数值 |

## 4 三项"外证里有、我们没查"的东西（一条已满足）

| 项 | mx 的收益 | 我们的现状 | 处置 |
|---|---|---|---|
| **Q5_1 / K-quant weight repack** | +84%/+74%（Q5_1）、+11%（本模型四卡） | 专家按 GGUF canonical 布局直接读；`moe_mmq_tab` 用 `expert_bytes` 步进 | **新立 R86（P0）** |
| **q8_1 激活复用**（同一激活被 q/k/v、router+gate/up 各量化一次 → 缓存） | +2.2~2.6%（bit-exact） | 本树 grep 无 q8_1 cache；每次 product 前都 `mmq::quantize` | **新立 R87（P1）** |
| **BF16→F32 compute type** | +18~19% prefill（UD/XL） | **已满足**：`src/prefill/gemm.cu` 全用 `CUBLAS_COMPUTE_32F` / `HIPBLAS_COMPUTE_32F` | 记一笔，不立项 |

## 5 新条目 R86：Q5_1 down 的布局重排

| 项 | 内容 |
|---|---|
| 目标 | down（Q5_1，43/48 层，88.6% 专家字节，占 prefill 13.8%）从 canonical 布局换成**两平面布局**：nibble plane + 第五位 word + half2 `d`/`m` 平面，行去别名（row stride 加 pad 避开 HBM channel stride） |
| 外证 | mx：Q5_1 dense 27B pp512 **+84%（单卡）**；Qwen3.8-Flash-Next MoE 43 个 Q5_1 tensor **+11% prefill（四卡 tensor）** |
| 本机预期 | down kernel +84% ⇒ 端到端 **−6.3%**（13.8% × (1 − 1/1.84)）；只拿到一半 ⇒ −3.2%，仍在门上 |
| 数值 | mx 记录 **Q5_1 单卡输出逐字节相同** ⇒ 预期无需 KL 门；仍要跑一次 `W913` 的 logits 对比确认（成本低） |
| 路径断言 | ①repacked blob 的 stride == `repack_gcn_nbytes(Q5_1, 640, 2560)`；②ISA 里 down 内核的 `v_add_u32`/`v_mul_lo_u32`（本机整 kernel 占 19.7%）显著下降；③服务端日志 `0 reused` |
| 关键工程点 | 我们是**按需上传**（prefill 每 chunk 借 2606 槽，7.62 GiB）：repack 必须**在上传后就地做**（GPU 侧一次核），不能假设全模型常驻。mx 的 `set_tensor` 是加载期重排，我们的等价点是 expert blob 落槽那一刻 |
| 依赖改动 | `moe_mmq_tab.cuh` 的 `expert_bytes` 步进 → `expert_stride`；`vec_dot_q5_1_q8_1_impl_mmq` 换 repacked 读法；新增一个 repack kernel（~60 行） |
| 不做什么 | 不动 gate/up 的 Q4_K（外证只有 +2~5%，投入产出比低）；不引 mx 的整套 buffer-type 框架（我们是自研 MoE 路径，不经过 ggml tensor） |

## 5.1 本机 canonical 基线（A 级，本轮实测，R86 的对照组）

同一个 `kq_bench`（生产同一份 `libstrata_mmq.a`），16 专家 × **320 token/专家 = 5,120 rows**（生产 chunk 16384 × top-10 ÷ 512 专家 ≈ 320）：

| 产品 | 形状 | 时间 | 吞吐 | 占微基准峰（21.52） |
|---|---|---:|---:|---:|
| **Q5_1 down**（43 层） | [2560, 640] | **1.53 ms** | **5.47 TMAC/s** | **25%** |
| Q8_0 down（5 层） | [2560, 640] | 1.78 ms | 4.70 TMAC/s | 22% |
| Q4_K gate/up（47 层） | [1280, 2560] | 2.26–2.57 ms | 6.5–7.4 TMAC/s | 30–35% |

- **Q5_1 的供给率只有 25%，比 gate/up 的 30–35% 更低** —— 与 milpster 的「Q5_K 1.30 cyc/byte vs Q6_K 0.74」是同一类结论：**5-bit 系的解包/缩放代价最重**。这正是 repack 宣称 +84% 的那一档。
- 口径：本轮三条都在**生产运行中**测（共享 GPU，Q4_K 三次 2.574/2.462/2.259 的 CV 偏大）；只用于量级与对照，正式 A/B 要在停服独占下重测。
- `expert_bytes`：Q5_1 [2560,640] = **1,228,800 B**、Q8_0 = 1,740,800 B、Q4_K [1280,2560] = 1,843,200 B ⇒ repack 后 stride 会变，`moe_mmq_tab` 的步进必须同步改。

## 6 R87：q8_1 激活复用（P1）

- 机制：一个 `attn_norm` 的输出被 q/k/v 三次量化、`ffn_norm` 被 router 和 gate/up 两次量化；缓存那份 q8_1 可省掉重复量化。
- 外证：**+2.2~2.6% prefill 与 decode，bit-exact**，默认开，`GGML_CUDA_Q8_1_CACHE=0` 可关。
- 本机：`mmq::quantize` 在 PMC 里只占 1.4%（单 product 视角），但整请求里它被调用 5 次/层 —— 需要先量"每请求量化总时间"，若 <1% 则不做（判据 `|Δ|≥2×CV`）。

## 7 下一步（顺序已改）

`R86（Q5_1 repack，先做单专家微基准）→ R85（attn 拆三段 → R46）→ R64 → R87 → R72 → R81 → R79/R80 → R49/R50/R30′`

R86 的第一步不是改生产，而是**扩展 `kq_bench`**：同一形状下跑 canonical vs repacked 两臂，量 Q5_1 down 的真实增益（我们的形状是 640×2560、每专家 ~320 token，不是 mx 的 27B dense）。
若单内核增益 <20%，R86 判否；≥40% 才值得动生产路径。

## 8 方法教训（写进纪律）

> **看一个 kernel 快不快，要同时看「怎么算」和「数据怎么摆」。**
> 上一轮我把 gfx906 社区的成果归纳成"tile 配置 + 内层循环"，于是得出了"五门全关"；而真正在**我们的模型**上被外证测到 +11% 的那一项（weight repack），连一行都没进过清单。
> 具体到取样方法：**按格式查，不按关键词查** —— 我们的 down 是 Q5_1，就应该直接搜 "Q5_1 gfx906 prefill"，而不是搜 "MMQ gfx906"。
