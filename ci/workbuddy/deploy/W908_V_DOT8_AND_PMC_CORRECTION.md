# W908 · 逐条核那张截图：三处硬错、一处真观察、一处该做的实验

> 2026-11-03 03:0x。零停服。每条都给出处：官方 ISA 文档 / hipfire 原文 / iacop 源码 / 同卡第三方实测。

---

## 0 先给结论

| 截图主张 | 判定 |
|---|---|
| gfx906 无 MFMA，量化乘只能走 `v_dot4_i32_i8`/`v_dot8_i32_i4` | **成立**（`v_dot4`/`v_dot8` 在 gfx906 有，`v_mfma` 只在 gfx908+） |
| gfx906 每 warp 每周期只有 1 个 dp4a 发射口 | **基本成立**（实测 dot4 达 21.7–22.3 TMAC/s ≈ 理论的 83%） |
| **decode 的 dp4a 卡在 ~48% VALUBusy** | **错**：48.5% 是 **prefill MMQ** 的 VALU；hipfire 的 decode GEMV 是 **25.9–41.4%**，且它自己的结论是"三个 GEMV 受 load-unit 限，只有 `gemv_residual` 是发射串行" |
| **`v_dot8` 是 8×int4×int8** | **错**：官方签名 `v_dot8_i32_i4 : dst, src0::i4x8, src1::i4x8`，**两个操作数都是 int4** |
| **iacop 用 v_dot8 重走 int4 权重** | **错**：iacop 全仓库 `dot8/sdot8` 命中 **0**，实际是 `ggml_cuda_dp4a` 101 处 + `sdot4` 1 处 |
| 我们的 decode 远没到顶、差在没用 `v_dot8` | **因果错**：M=1 时算术强度 1.78 MAC/B，要喂满 dot4（21.7 TMAC/s）需 **12 TB/s**，HBM 只有 ~1 TB/s ⇒ decode 天然受带宽限，加宽指令不减少字节 |
| 截图里唯一说对的**观察** | prefill 的 MMQ 在 gfx906 上确实被 dp4a 发射率压住（48.5% VALU）；而**我们自己的 prefill 只有 ~21%** ⇒ 真实的 2× 差距在我们这边，不在指令 |

---

## 1 `v_dot8` 到底是什么（官方签名，逐字）

LLVM `AMDGPUAsmGFX906` 的 VOP3P 表：

```
v_dot4_i32_i8  vdst, src0::i8x4, src1::i8x4, src2::i32  clamp
v_dot8_i32_i4  vdst, src0::i4x8, src1::i4x8, src2::i32  clamp
```

⇒ `v_dot8` 是 **8 个 int4×int4**。要用它，**两侧都得是 4-bit**：权重本来就是 4-bit（Q4_K 打包），
但我们的激活是 **Q8_1（int8）**。把它降到 int4 就是 **W4A4**，等于再丢一档精度（见 `W905` 的精度账）。

hipfire 自己也是这么说的（原文）：

> "Caveat: int4-natively dp doesn't match our int8-packed Q8_1 activations on the y side … y would need to be int4-quantized too for the symmetric dp8."

并且它把这条明确标成 **未实现的推测**：

> "`v_dot8_i32_i4` … Now the single biggest remaining lever … **Highest expected payoff.**"（列在 Follow-up work 第 1 项，未做）

## 2 iacop 到底有没有用 `v_dot8`（源码计数）

```
grep -rIni 'dot8|sdot8' . --exclude-dir=.git   →  0 处
__builtin_amdgcn_sdot4  → 1 处
ggml_cuda_dp4a (→ sdot4) → 101 处
```

⇒ 截图里"iacop：int4 权重重走 `v_dot8`"是**凭印象写的**。它附带的 `SCRIPT_overclock_upp_MI50.sh`
**确实存在**（3,047 B），这一点截图是对的；但超频与指令选择是两件事。

## 3 48% 到底属于谁（hipfire 原文数值）

| Kernel | VALUBusy | MemUnitStalled |
|---|---:|---:|
| `fused_gate_up_*_wave64`（decode） | **41.4%** | 4.12 |
| `fused_qkv_*_wave64`（decode） | 37.2% | 4.00 |
| `fused_qkvza_*_wave64`（decode） | 37.9% | 4.23 |
| `gemv_residual_*_wave64`（decode） | **25.9%** | 0.95 |
| **`gemm_*_mmq_gfx906_full_set_x64`（prefill）** | **48.5%** | 0.3 |

hipfire 的结论是**分内核**的，不是一句"decode 卡在 48%"：

> "The three sister kernels sit at 37-41% VALUBusy … **Their bottleneck is the load unit's queue depth / HBM round-trip latency.**"
> "The bottleneck in `gemv_residual` was **instruction-issue serialization**, not L2 hits."（引入 prefetch 后 25.6→33.3%）
> prefill 那 48.5% 才是 "**hardware issue-rate limit on dp4a**, not a software ILP limit"。

而截图把 prefill 的数字搬到了 decode 上，再由此推出"要用 v_dot8 救 decode"——**前提就错了**。

## 4 decode 为什么加宽指令救不了（算术强度，一算就清楚）

- Q4_K 权重：256 值/144 B ⇒ **0.5625 B/权重**。
- **M=1**（decode 每个 token）：每个权重只用一次 ⇒ **1.78 MAC/B**。
- 要喂满 dot4 的实测上限 21.7 TMAC/s ⇒ 需要 **12.2 TB/s**；MI50 HBM ≈ **1.02 TB/s**。
⇒ **差 12 倍，decode 是带宽/延迟问题**。加宽指令（dot4→dot8）只减指令数，**一个字节都不减**。

旁证两条（都是实测，不是推理）：
- ki 的 `dense_gemv` 在 M=1 上做到 **"3114 vs 3128 µs ≈ 98% 内存地板"**（`W906`）；
- 我们的专家读 **411 GB/s**，对纯读探针 **487 GB/s = 0.84×**（`W891`）。

所以截图那句"你这张卡的 decode 远没到顶，问题是没用 v_dot8"——**方向错**。decode 到没到顶，
看的是**有效带宽/纯读地板**，我们已经 84%，ki 是 98%，差 14 个点，不是 2 倍。

## 5 但它有一处真观察，而且指向我们真正的缺口

**prefill 的 MMQ 在 gfx906 上被 dp4a 发射率压住（48.5% VALU）——这是真的。而我们在 ~21%。**

按 `W903` 的生产相位（gate/up 2210 ms / 7993 token / 48 层 / top-8 / n_ff≈640）反推：
**≈4.55 TMAC/s**；对照同卡实测上限 **21.7 TMAC/s**（skyne98 wiki，ILP4 下 43–44 TOPS）⇒ **我们 ≈21%**。

> **同时修正我自己**：`W904` 把 dp4a 上限写成 **19.07 TMAC/s**（我那次探针只用了 4 个累加器）。
> 第三方在同一张卡上用 ILP4 测到 **21.7–22.3 TMAC/s**、理论 26.5 ⇒ 我那个"墙"偏低约 12%。
> 但结论方向不变（我们离墙更远），见 `W904` 的更正横幅。

**差距在 21% → 48% 这一段，也就是 R60（K 切分/并发流）与 R58（三段计数）要打的**，
不是"换 v_dot8"（那要把激活降到 int4，换来的是 2× 指令密度、丢掉 Q8_1 的精度）。

## 6 该做的那个实验（这才是截图里唯一值得照做的东西）

hipfire 的 48.5% 是 **PMC 口径**（rocprof 的 VALUBusy / MemUnitStalled / FetchSize）；
我们到今天为止**所有**关于 MMQ 的结论都是**时间口径**（TTFT、ms/window）。两者不能互换——
`W902`（微基准 3.14× → 真核 0%）和 `W904`（解包 hoist → 慢 6–10%）都是因为缺 PMC 而判错方向。

⇒ **新条目 R61**：用 rocprof 量我们 prefill MMQ 的 `VALUBusy / MemUnitStalled / FetchSize / L2 hit`。
判据很简单：**若 VALU ≥ 40%，我们已接近 hipfire 的墙，R60 不必做；若 VALU ≤ 25%，差距是真的，R60 必须做。**
这一步零代码改动，只加一个 profiling 依赖（容器里已有 rocprof）。

## 7 一句话

截图"gfx906 没有 MFMA、dp4a 有发射率上限"是对的；但它把 **prefill 的 48%** 安到 decode 上、
把 `v_dot8` 写成 **int4×int8**（实为 int4×int4）、说 **iacop 用了 v_dot8**（源码 0 处）——
三处硬错导向了错误结论。它唯一有价值的提醒是：**该用 PMC 而不是墙钟去判断 MMQ 到底卡在哪**，
而这正是我们一直缺的那把尺子（R61）。

---

## 8 逐条一一对应（截图/ki/iacop 的每一项 → 我们源码在第几行）

口径同 `W907`：每条给出**我们的位置**；"——"表示这项在我们的代码里不存在。

| # | 条目（截图里说的） | 对方有什么 | **我们有什么** | 我们的位置 | 判定 |
|---|---|---|---|---|---|
| 1 | gfx906 无 MFMA | — | **确认没有**；全树唯一一处 `v_mfma` 是注释在说"不可用" | `include/strata/kernels/gfx_arch.hpp:35`（"saturating forms (*c) and v_mfma are not"） | 一致 |
| 2 | 量化乘只能走 dot4 | iacop：`ggml_cuda_dp4a` **101 处** + `sdot4` 1 处 | **有**：全树 `sdot4/v_dot4` **7 处**；K-quant MMQ 全部经 `ggml_cuda_dp4a` | overlay `vecdotq.cuh:541`（`vec_dot_q4_K_q8_1_impl_mmq` 内）+ 7 处自有引用 | 一致 |
| 3 | `v_dot8_i32_i4` | iacop **0 处**；hipfire 只写进 follow-up（未做） | **0 处真指令**。全树 37 个 `dot8` 命中**全是函数名**：`dot8u`/`dot8u_ptr`（`fused_gr.cu:87/99`）、`dot8`（`qsa_pattn.cu:152`），做的是 FP32/BF16 的 8 元素点积 | `fused_gr.cu:87`、`qsa_pattn.cu:152` | **一致**（两边都没用；这也是 `W906` 里那张"dot8 命中数"表的来源） |
| 4 | 每 warp 每周期 1 个 dp4a 发射口 | 硬件事实 | 不适用；我们实测 **19.07 TMAC/s**（我的探针），第三方 ILP4 **21.7–22.3** | `W904`（已加更正横幅）/ `W908 §5` | 一致 |
| 5 | prefill MMQ VALU **48.5%** | hipfire 实测（`gemm_*_mmq_gfx906_full_set_x64`） | **我们没测过**（只有 TTFT / ms-window 的时间口径） | —— | **缺口 → R61** |
| 6 | tiled MMQ | iacop/llama.cpp 有 | **有**：`MMQ_TILE_NE_K` 与 gcn 表 11 行 Q4_K（`256 threads / nwarps 2 / I 64–128 / J 8–64`） | overlay `mmq.cuh`、`mmq-config-gcn.cuh:120–130` | 一致（差的是 `stream_k=false` → R60） |
| 7 | LDS 暂存 | 有 | **有**：MMQ 的 `x_qs`/`y_qs` 共 **105 处**；我们自有内核另有 **31 处** `extern __shared__` | `mmq-vec-dot.cuh`；`src/kernels/cuda/*.cu`（31 处） | 一致 |
| 8 | Q8_1 预量化激活 | 有 | **有，且多一层去重**：`native_quantize_q8_1_kernel` + `x_q8_1_ready` 跳过同一激活的重复量化 | `native_mmvq.cu:158`、`core/layer.cpp:168–178` | 一致（我们更强） |
| 9 | int4 权重重打包 | iacop 有 | **有**：`--pack` + `tools/iq_pack.py` + `native_experts.txt v4`（生产 `--pack /data/packs/ud-q4_k_xl`） | 生产 CLI + `tools/iq_pack.py` | 一致 |
| 10 | `SCRIPT_overclock_upp_MI50.sh`（UPP 超频） | iacop 有（3,047 B） | **没有，且不需要**：decode 期间 sclk 已钉 **1725 MHz 最高档**、功耗 114–220 W 未撞 300 W 墙 | `W892 §5` / R48（DONE_NEG） | **不同**：我们量化过，超频无空间 |
| 11 | "decode 卡 48% → 用 v_dot8 救" | — | **不成立**：M=1 算术强度 1.78 MAC/B，喂满 dot4 需 **12.2 TB/s**（HBM 1.02 TB/s） | `W908 §4` | 否决 |
| 12 | "带宽只有十几%" | — | 按峰值 1 TB/s 算是 15%，但 M=1 的**可实现地板**是纯读 487 GB/s；我们 **411 GB/s = 84%** | `W891` | 数字口径不同：我们离自己地板只差 16% |

**合计：12 条里 8 条我们已有（其中 #8 比对方多一层去重）、1 条是真缺口（#5 PMC 口径，已立 R61）、
1 条我们明确不做（#10 超频，R48 已量化否掉）、2 条是对截图推论的否决（#11/#12）。**

**这张截图真正缺的东西**：它没有说"我们的 MMQ 现在 VALU 是多少"。hipfire 的 48.5% 是**别人的核**；
把 48.5% 当成"我们的现状"，再用它推出"上 v_dot8"，中间少了测量这一步。R61 补的就是这一步。
