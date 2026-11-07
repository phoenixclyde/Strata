# W779 KIntegrated 项目的 gfx906 优化：哪些能移植到 Strata

> 2026-10-24 03:4x-04:1x · 机主令「看一下 ki 的项目有关 gfx906 的优化代码有没有可以移植过来的」
> 源：`KIntegrated/vllm-gfx906-mobydick`（24 个分支，最后一次 push 2026-10-23T19:27Z）
> 目标：Strata 0.2.3 / 引擎 0.1.48.1（生产 `strata166-407`）

---

## 0 结论

**代码级可移植价值低，结论级价值高。**

理由一句话：**两边都是手写的 gfx906 kernel，而且 Strata 已经在用同一套硬件手法**——不是"一个优化过的对一个没优化的"。
真正能拿过来的是它那张**死路索引**和**测量纪律**，以及三个还没试过的方向。

---

## 1 先看资产构成（不是所有东西都叫"优化代码"）

| 资产 | 位置 | 量 | 可移植性 |
|---|---|---|---|
| **gfx906 手写 FlashAttention** | `csrc/gfx906_fa/`（fa.cpp 56 KB、fa_gather.cu 33 KB、launcher.cu 27 KB、quant.cu 8.4 KB + kernel/） | ~124 KB | **低**：接口/布局是 vLLM 的 paged KV，Strata 是自有 QSA layout |
| **MoE 相关** | `csrc/moe/`（只有 `dynamic_4bit_int_moe_cpu.cpp` 6 KB） | 6 KB | **无**：CPU 版，我们是 GPU |
| **量化** | `csrc/quantization/w8a8` | 小 | **低**：AWQ/W8A8 vs 我们 GGUF IQ4_XS，格式不通 |
| **gfx906 文档库** | `docs/gfx906/`（45 个文件，约 500 KB） | 大 | **高**：纯结论，直接可用 |
| **测量脚本** | `benchmarks/kernels/gfx906/`（35 个 probe） | 大 | **中**：思路可借，脚本绑 vLLM 接口 |
| **硬件手法笔记** | `lds-layout.md` / `latency-hiding.md` / `dequant-instructions.md` | 5.7 KB | **高（但已覆盖）**，见 §3 |

---

## 2 最重要的一份：`DEAD-ENDS.md`（4940 B，一行一条）

它的格式是 `假设 -> 门 -> 裁决 -> commit -> 注释`，全部是 gfx906 上实测过的否定证据。**其中有 3 条直接对应我们的场景**：

| 它的记录 | 对我们的直接含义 |
|---|---|
| **`P3-2(b) K-split GEMV 假设 -> REJECTED（错）`**：`kc=512 比 LLMM1 慢 2.4-4.2 倍`，结论 **"M=1 是 latency/launch-bound，不是 occupancy-bound"** | 我们 decode 也是 M=1。**"把 GEMM 拆开喂更多并发"这条路在 gfx906 上已被实测否掉**，我们不必再试 |
| **`gemm1 NPT=2 -> DEAD-END（neutral）`**：census 说 `-186 µs/step`，但墙钟中性，"第 3 次连续 transfer 失败" | 与我们的经验同源：**微基准/计数器的收益不等于墙钟收益**。我们 `--pool-tasks`（483.4 vs 484.3）就是同一现象 |
| **`FA V2 fused gather -> REJECTED（V1 wins）`**：V2 在 serving 里退化 **7 倍**（285 µs vs 42），原因是 wave-scheduling/low-WG | 我们若要动注意力 kernel，**必须用 serving 墙钟做门，不能用 standalone** |

它自己总结的三条纪律，与我们踩过的完全一致：
1. **standalone harness 的胜利不迁移到 serving 墙钟**（连 eager 都不迁移）
2. **serving A/B 才是 µs 级裁决的唯一门**
3. PPL/prompt_logprobs 在 hybrid attention 模型上不可靠

---

## 3 反向确认：Strata 的 kernel 不缺 gfx906 的 LDS 手法

它的 `lds-layout.md` 给了一条很硬的实测：gfx906 上列式 LDS 访问，`ld=32`（2 的幂）只有 **1865 GB/s**，`ld=33`（+1 vec4 padding）回到 **3974 GB/s**（差 2.1 倍）。

我拿这条去核对 Strata 的 kernel，结果是**已经不缺**：

| Strata 位置 | 手法 |
|---|---|
| `dflash2.cu:107` | `__shared__ float Sc[32 * 33];` —— **正是 ld=33 padding** |
| `dflash2.cu:239` | `pbase[tid * 130]` —— 130 = 2×65，同类 padding |
| `qsa_decode_attn.cu:355` | `__align__(16) float spt[CHUNK][G];  // cell-major: one cell's 12 heads are 3 float4` —— **用转置布局 + float4 消除冲突**（另一种等价解法） |
| 全目录 | `__shared__` 324 处、`uint4/float4` 362 处、`__shfl_xor_sync` 多处（HIP 映射到 DPP 或 ds_bpermute） |

`native_mmvq.cu` 的 `partial[WARPS-1][ROWS][WARP]` 是归约缓冲，不是列式消费，加 padding 无意义。

**所以"把 routeK 的 LDS 技巧搬过来"这个方向没有空缺。** 两边各自用了不同但同级的方案（padding vs 转置），谁更快只能靠 profiler，不能靠文档。

它的 `latency-hiding.md` / `dequant-instructions.md` 同样是硬件事实清单（DPP 比 LDS+barrier 快约 2 倍、b128 LDS 最强 9.5-11.2 TB/s、`v_mfma*` 在 gfx906 不存在、只有 dot4/dot8 没有 dot4c/dot8c）—— 这些与 register 里已有的 P38 结论（dot4 62,596 / dot8 0）一致，**无新增**。

---

## 4 它 SHIPPED 的两项，与我们能不能对上

| 它的成果 | 数据 | 对我们 |
|---|---|---|
| **Spec-decode MTP k=2** | 39.4 t/s（1.41×），1.82 tok/step | 我们是 `--spec 4`（被 suffix-draft 涨到 6）、`mtp_max 4`。**k 值方向相反（它 2、我们 6）**，说明这个最优值强依赖实现，不能照搬；但"1.82 tok/step"给了我们一个对照基准（我们 `drafts_accepted/drafts_offered` 可从 `/metrics` 读） |
| **W1 GDN mixed-batch chunk reclass** | 27B 混合 2 请求 ngram 服务 **+6.7%**（59.35 vs 55.60），kernel spy 把 2016 次浪费的 chunk 调用减到 0 | **我们没有 GDN 层**（pack `index.txt` 里 `gdn` 出现 0 次），不适用 |

---

## 5 一条差点被当成"可移植点"的空宏（查完作废）

它的 `csrc/gfx906_fa/kernel/gfx906-config.h`（1.1 KB）里有一条看起来正合我们口味的：

```c
#ifdef GGML_HIP_GFX906
#define GFX906_MMQ_NWARPS 2
```

而 Strata 用的 ggml（pin `3cf03257`）在 `ggml/src/ggml-cuda/mmq.cuh:11` 是 `#define MMQ_NWARPS 8`。
**8 vs 2，看起来像一条现成的预填补丁。** 查完是空的：

1. 这套 FA 的 `ggml_shim.cuh` 开头是俄语注释，原文写着它**是从 llama.cpp 的 `fattn-q8.cuh` 复制出来的**，只为了让它在 PyTorch 扩展里编译、不链接 ggml；
2. 在 `ggml_shim.cuh` 里 **`MMQ_NWARPS` 一次都没被引用**；
3. 上游 ggml 的 gfx906 路径走 `mmq.cuh:263` 的 `#ifdef GCN -> ggml_cuda_mmq_get_config_gcn`，`MMQ_NWARPS 8` 是**全局常量**，与那个宏无关。

=> **不能移植**。这是本轮唯一一个"看着能搬、查完作废"的点，记在这里免得以后再翻。

---

## 6 一条值得对照的调优规则（未验证）

`DEVLOG-moe-opt.md` 的 Phase 2 prefill tuning 里有个 SHIPPED 的启发式：

> **BM=8 for prefill（BIG WIN）**：`em > 512 -> BM=8, NPT=2`，heuristic **`<=32 -> 1, <=512 -> 4, else 8`**

即 MoE GEMM 的 block-M **按一次要算的专家行数分档**，不是固定值。
Strata 的预填同样是"按 chunk 内专家行数做 grouped GEMM"（`native_moe.cu` / `moe_hit_grouped_s2`），
**是否已经按行数分档、BM 是否编译期常量**——这两点没查过，属于下一轮可以查的（**只是查，不是搬**）。

---

## 7 可以立刻拿过来用的三样（不是代码）

1. **`DEAD-ENDS.md` 当作我们的前置过滤器**：以后要走"拆 GEMM 提并发""微基准赢就上"这类路，先查它有没有撞过（已撞两条）。
2. **测量纪律对齐**：它的 "serving A/B 是唯一门" 与我们 W778 的结论一致（pool-tasks 微基准 + 实际零收益），可以互相引用，把这条写进 register 的方法论。
3. **三个 probe 思路**：`mtp_shape_spy.py`（MTP 形状）、`spec_step_probe.py`（每 step 的 token 数）、`prefill_ttft_probe.py`（预填首字）。我们的 `/metrics` 已能给 `drafts_offered/accepted`、`prompt_ms`、`decode_ms`，**功能重叠，不必搬脚本**。

---

## 8 明确不做的

| 项 | 理由 |
|---|---|
| 搬 `csrc/gfx906_fa/` 的 kernel 源 | 接口与 KV 布局完全不同（vLLM paged vs Strata QSA）；且它的 V2 gather 在 serving 里退化 7 倍，说明这套 kernel 的收益高度依赖调度形态 |
| 搬 `csrc/moe/` | 只有一个 CPU 实现 |
| 搬 `csrc/quantization/w8a8` | 模型量化格式不同（AWQ W8A8 vs GGUF IQ4_XS） |
| 搬 LDS/DPP 手法 | Strata 已在用（§3） |
| 照搬 MTP k=2 | 与我们的 `--spec 6` 方向相反，最优值随实现变 |

---

## 9 一句话

**它的"代码"搬不动（布局不同），它的"结论"很值钱（我们正打算试的两条路它已经撞过墙），而它最硬的那条硬件优化（LDS ld=33）Strata 早就自己做了。**
