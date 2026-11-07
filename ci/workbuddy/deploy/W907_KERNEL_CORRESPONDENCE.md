# W907 · 逐内核对照：ki 的 12 个 gfx906 内核 vs 我们的 364 个

> **【AUDIT24 P1 · 2026-11-04】内核总数与 `W912` 冲突**：本件写「12 个 / 5,220 行」，`W912` 逐文件读后写
> 「19 个 / 5,703 行」。两者都自称逐文件盘点 ⇒ 以 **`W912` 的 19 个**为准（本件漏计了散在 `qwen4exp` 子目录的 7 个）。
> 另：本件「ki 的 FA 可以直接复用」的结论已被 `W912`（逐文件判决）取代。

> 2026-11-03 03:0x。零停服。ki 侧源码 `KIntegrated/vllm-gfx906-mobydick @3857591`（本地 `albus/w896/forks/ki-latest`），
> 我方源码 `pr/strata-fork @ d963c791`。每一条都带文件:行号。

---

## 一句话

**ki 总共 12 个 gfx906 内核（5,220 行）**；我们能一一对应上 **7 个（且更全）、缺 2 个（MoE GEMM）、
2 个走完全不同的算法（QSA）、1 个我们用 host+gather 代替**。唯一的真缺口恰好是 prefill 里最贵的那块。

---

## A. ki 的 12 个内核（全部源码定位）

| # | 内核 | 文件:行 | 启动配置 | 机制 |
|---|---|---|---|---|
| 1 | `dense_gemv_kernel` | `dense_gemv_gfx906.cu:133` | `__launch_bounds__(KCHUNK/8)`；KCHUNK 512/1024/2048/4096 ⇒ **64/128/256/512 线程 = 1/2/4/8 波** | fp16 W16A16，每线程沿 K 取 16 B |
| 2 | `dense_gemv_m_kernel` | `:272` | 同上 | M>1 |
| 3 | `dense_gemv_m_kernel_rt` | `:419` | 同上 | 运行期 tile |
| 4 | `dense_gemv_m_kernel_m16` | `:573` | 同上 | M=16 |
| 5 | `dense_gemv_i8_kernel` | `:697` | `__launch_bounds__(KC/16)` | int8 权重 |
| 6 | `dense_gemv_i8_m_kernel` | `:820` | 同上 | int8，M>1 |
| 7 | `dense_gemv_i8_scale_kernel` | `:982` | — | 输出缩放 |
| 8 | `moe_gemm_q4_kernel_gfx906` | `moe_q_gemm_gfx906.cu:161` | `THREADS_X=256`（**4 波**）、`BLOCK_KN_SIZE=256`、NPT 4/2 | **W4A16**，`__ockl_fdot2`，CAS 原子累加 |
| 9 | `moe_gemm_q4_v2_kernel_gfx906` | `:398` | 同上 | v2 |
| 10 | `moe_align_m1_gfx906_kernel` | `moe_align_m1_gfx906.cu:54` | `<<<1, THREADS>>>` | M=1 专家行对齐 |
| 11 | `flash_attn_tile_q8` | `fattn-q8.cuh:920` | — | Q8 K + fp16 V 的 dense FA |
| 12 | `flash_attn_tile_q8_paged` | `fattn-q8-paged.cuh:417` | — | 分页 KV 版 |

## B. 一一对应（这是我们这边"有多少"的正面回答）

| ki | 我们的对应 | 位置 | 判定 |
|---|---|---|---|
| 1–4（fp16 GEMV 四态） | `native_q4_k_mmvq_kernel` / `native_q5_k_mmvq_kernel` / `native_q6_k_mmvq_kernel` / `native_q2_0_mmvq_kernel` / `native_q3_k_mmvq_kernel` / `native_iq4_xs_mmvq_kernel` / `native_mmvq_multi_kernel` / **`b6_mmvq_rows_kernel`（R23 运行期行数表）** / `native_mmvq_wave_kernel` | `native_mmvq.cu:601/257/736/325/413/506/1244/**1481**/2396` | **对等且更全**：ki 只有 fp16 与 int8 两族，我们有 **6 种量化格式**各自一条 |
| 5–6（int8 GEMV） | `native_q8_0_packed_kernel` / `native_mmvq_il_kernel` | `native_mmvq.cu:2558/2156` | 对等 |
| 7（i8 scale） | `quantize_act.cu` 9 个 kernel | `src/kernels/cuda/quantize_act.cu` | 对等 |
| **8–9（MoE GEMM）** | **HIP 下没有**：`gemm_iq_f16_grouped_kernel` 在 `#if !defined(__HIPCC__)` 里（`iq_kernels.cu:6658`，Volta WMMA）。生产 prefill 走 llama.cpp MMQ | `iq_kernels.cu:6667`（编译掉） | **缺口** |
| 10（M=1 专家对齐） | 无同名 kernel；prefill 用 **host grouping + gather** | 生产日志：`host grouping 58 ms`、`gather 34 ms` | 形式不同（我们部分在 host） |
| 11（dense FA） | `qsa_decode_attn.cu`(7) / `qsa_prompt_attn.cu`(7) / `qsa_select.cu`(24) / `qsa.cu`(8) / `native_qsa_indexer.cu`(5) | `src/kernels/cuda/qsa_*.cu` | **算法不同**：我们走 QSA 稀疏索引，不是 dense FA |
| 12（paged FA） | `kv_stream.cu`(4)：KV 驻 RAM、按需搬 | `src/kernels/cuda/kv_stream.cu` | **部分**：我们不做 paged-FA |

**比分：7 对等（其中 GEMV 族我们更全）／2 缺失（MoE GEMM）／1 换实现（host+gather）／2 不同算法（QSA）。**

## C. 规模：我们这边到底有多少"gfx906 专用"

| 口径 | 数字 |
|---|---|
| `src/kernels/cuda/` 的 `__global__` 总数 | **364**（含 `#if !defined(__HIPCC__)` 的 CUDA-only 分支，实际 HIP 可用少于该数） |
| 显式带 `gfx906`/`GFX906` 标记的文件 | **7** 个：`qsa_decode_attn.cu`(27 处) / `iq_kernels.cu`(13) / `fused_gr.cu`(11) / `router_top10.cu`(6) / `native_mmvq.cu`(4) / `verify_kernels.cu`(3) / `qsa_prompt_attn.cu`(2) |
| gfx906 专用**开关**（源码引用数） | `HC_Q8`(44)、`ROUTE_TAIL_SKIP`(21)、`SELECT_SIMT`(16)、`GDN_HEAD`(12)、`GDN_PP`(10)、`ATTN_QUERY_SWIZZLE`(5)、`GFX906_ATTN_REDUCE12`(4)、`MMQ_KQ`(2)、`HIP_PROMPT_F16`(2) —— 共 **9 个** |
| ki 的 gfx906 专用内核 | **12 个 / 5,220 行** |

**我们独有、ki 完全没有的**：`fused_gr.cu`(28) 与 `gdn.cu`(5)、`native_gdn_preprocess.cu`(5) 的 GDN 融合链；
`ple.cu`(9) 的 PLE；`dflash2.cu`(20) 的草稿模型；`shared_expert.cu`(11)；`sampler.cu`(11)；`elementwise.cu`(18)；
`qsa_select.cu`(24) 的基数选择。这些是架构差异（Qwen3.8-Flash-Next 的 GDN/QSA/PLE），不是 ki 的遗漏。

## D. 缺口怎么补（只补那 1 个真缺口）

缺的是**自有的 MoE 专家 GEMM**（prefill 34.6%），而我们的 WMMA 版只为 Volta 写、在 HIP 下连编译都不参与。
两条路，按代价排序：

1. **R60（已做，已编译通过）**：把我们 llama.cpp MMQ 的 Q4_K 从 `stream_k=false`（整条 K，ki 实测慢 2.2–4.3× 的
   full-K 形状）改成 stream-k。**借的是 ki 的机制结论，不搬它一行代码**，也不动权重格式。
2. 若 R60 不过门：**把 `gemm_iq_f16_grouped` 的 tile 结构改成 gfx906 可用的 dp4a 版**
   （WG_BM=64 / WG_BN=128 的骨架保留，`nvcuda::wmma` 换成 dp4a + LDS 分块）。这是一次真正的内核开发，
   代价远大于 R60，且必须先有 R59 的精度门才能验收。

## E. 这一节的结论

**"ki 有的我们有多少"**：12 个里 7 个对等或更强、2 个缺、2 个不同算法、1 个换成 host 路径。
"针对 gfx906 专门写/优化"这件事我们并不落后（364 个 `__global__`、9 个硬件开关、6 种量化格式的 MMVQ），
**落后的只有一处：专家的多 token GEMM 是我们借来的**，而它正好是 prefill 里最大的一块。
