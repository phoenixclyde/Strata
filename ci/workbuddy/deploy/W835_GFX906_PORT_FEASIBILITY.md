# W835　gfx906 专项优化的移植可行性（源码级判定）

> 对象：166 上的 **KI**（KIntegrated/vllm-gfx906-mobydick）与 **llama.cpp**（含 gfx906 fork 生态），
> 以及 **Strata 本项目**里"别的架构的优化能否扩展到 gfx906"。
> 判定口径：每条都要有 **gfx906 指令前提（汇编器实测）** + **Strata 现状（文件:行）** + **落点与预期**。
> 出具日期 2026-10-31。生产未改动。

---

## 0 生产现状（本轮快照 14:47:52）

| 维度 | 值 |
|---|---|
| 容器 / 镜像 | `strata166-407` Up 15 min / **`strata-gfx906:0.2.8p2`** |
| 引擎 | `/data/bin/strata-0.1.54n2`，**33 args / 14 env** |
| 显存 | **33.5 / 34.3 GB = 97.4%** |
| 专家缓存 | **7463 槽 / 21.79 GiB**；提示借用 **1578 槽 / 4.62 GiB** |
| 预热 | 7463/7463 槽 **1.8 s（12739 MB/s）** |
| `/health` | ok，`max_context 262144` |

---

## 1 先钉死指令真值：生态里有一处流传很广的错误

三种来源对"gfx906 有没有 dot 指令"说法互相矛盾，必须先用汇编器裁定（`/opt/rocm/llvm/bin/llvm-mc -mcpu=gfx906`，本轮实跑）：

| 指令 | LLVM 文档字面 | 实测汇编 | 结论 |
|---|---|---|---|
| `v_dot2_f32_f16` | gfx9-generic 条目下列为"gfx906 不可用" | **OK** | **可用** |
| `v_dot4_i32_i8`（dp4a） | 同上 | **OK** | **可用** |
| `v_dot8_i32_i4` | 同上 | **OK** | **可用** |
| `v_dot4c_i32_i8` / `v_dot8c_i32_i4` | 不可用 | **NO**（`instruction not supported on this GPU`） | 确实没有：**不能依赖 dot4c 折叠** |
| `v_mfma_f32_16x16x16_f16` | 不在 gfx906 页 | **NO** | 确实没有：**无 MFMA** |
| `v_mov_b32_dpp` | — | **OK** | **DPP 可用** |

**两处必须点出来的错**：

1. **LLVM 文档那句是 gfx9-generic 的联合限制**（gfx900/902/904 没有 dot，所以 generic 目标不能发）。skyne98 也独立用 `llvm-mc` 验过同一结论。**照字面读会得出"gfx906 不能做 int8/fp16 点积"的反向结论。**
2. **KI 的源码直接踩了这个坑**：`csrc/rocm/dense_gemv_gfx906.cu:600` 注释逐字
   `gfx906 has no integer dot product, so the MACs run through the existing __ockl_fdot2 chain`，
   因此它的 AWQ W4A16 路径**全部走 fp16 dot2，完全没用 dp4a**。
   **反例就在我们自己的机器上**：Strata 的 `STRATA_DP4A` 走 `v_dot4_i32_i8`，`STRATA_MMQ_KQ=1` 实测 **+68% prefill**（P198）。

⇒ 这一条本身就是**可回馈社区**的硬发现：gfx906 上 dp4a 不仅可用，在我们这个形状上比 fp16 点积更快。

---

## 2 166 上到底有什么

| 线 | 路径 | 状态 |
|---|---|---|
| **KI** | `/home/albus/routeK/base/KIntegrated-mobydick` | commit `6ccbb03`，gfx906 专项集中在 `csrc/gfx906_fa/`（FA gather/quant、`fattn-q8.cuh`、`q8_0_quantize.cuh`）+ `csrc/rocm/{dense_gemv, moe_q_gemm, moe_align_m1}_gfx906.cu` |
| **KI 来源** | `gfx906-config.h` 头注释：`Vendored from https://github.com/cassettesgoboom/gfx906-fa-vllm`，`Copyright (C) Nick` | 即 `nick413-bit/gfx906-fa-vllm`（166 上也有），其上游是 **skyne98** |
| **llama.cpp** | `/home/albus/strata166/src028/third_party/llama.cpp`（ggml 上游 `3cf0325`）+ `llama.cpp-3cf0325.tar.gz` | **只有上游，没有 gfx906 fork 源码** |
| **llama.cpp-gfx906** | `docker.1ms.run/mixa3607/llama.cpp-gfx906:v0.5.0-rocm-7.14`（7.86 GB，5 周前） | **只有二进制镜像**。手法与 KI 同源（skyne98），代码结构是 ggml，与 Strata 完全不同 |

⇒ **结论：llama.cpp 这条线能移植的是"手法"，不是"代码"**（ggml 的 `blck`/`ggml_tensor` 与 Strata 自研引擎没有共享层）。KI 这条线有**可读的源码**，价值更高。

---

## 3 逐项移植判定（源码级）

Strata 现状用 `grep` 全库统计（49 个 `.cu`，路径 `src028/src/kernels/cuda/`）：

| # | 手法 | 来源 | gfx906 前提 | Strata 现状（实测计数） | 可移植性 | 落点 |
|---|---|---|---|---|---|---|
| 1 | **LDS 隔行 +1 vec4 padding**（ld = K_vec+1） | skyne98 实测：`ds_read_b128` 列式访问 **1865 → 3974 GB/s（2.13×）** | 无（纯布局） | **仅 2 处**：`dflash2.cu:107 Sc[32*33]`、`qsa_select.cu:1157/1262 so[TS_Q][TS_KB+1]`。其余 `__shared__` 声明**均无 pad** | **可直接搬**，零算法风险 | 所有"列式消费"的 tile（`qsa_decode_attn` 的 `sp[G][CHUNK]`/`spt[CHUNK][G]`、`qsa_select` 的 `so`） |
| 2 | **DPP 归约替代 `ds_bpermute`** | llama.cpp-gfx906 首要项 "DPP-based warp reductions" | `v_mov_b32_dpp` **OK** | **部分已有**：`qsa_decode_attn.cu:478` 用 `__builtin_amdgcn_mov_dpp`，注释写明"instead of ds_bpermute，因为 score 循环被 LDS 管道卡住"。但全库 **`__shfl_xor` 193 处 / 31 文件**，`dpp` 仅 2 处 | **可直接搬**（作者已认可这条思路） | `native_router.cu`（3 处归约循环）、`fused_gdn.cu:120`、`fused_gr.cu`、`qsa_select.cu` |
| 3 | **`v_dot2_f32_f16` 做 fp16 MAC** | llama.cpp fork 的 `fattn-tile-f16-gfx906.cu`；KI 的 `__ockl_fdot2` 模板（`dense_gemv_gfx906.cu:88`、`moe_q_gemm_gfx906.cu:55`） | **OK** | **全库 0 处**。`native_mmvq.cu` 里的 23 处 `dot2` 是 `STRATA_DP4A`（int8），**不是** fp16 dot2 | **可搬，但必须过精度门** | `fused_gdn.cu:115-118`（现用 `__uint_as_float(w<<16)` + `fmaf` 把 **bf16→fp32** 再算）、`native_qsa_score.cu:76/166`（逐元素 `fmaf`）、`native_flash_attn.cu:93-94/123-124`（`__half2float` 解包后 `__fmaf_rn`） |
| 4 | **int8 dp4a** | — | **OK** | **已有**（`STRATA_DP4A` → `v_dot4_i32_i8`） | **我们已领先**，可反向输出 | — |
| 5 | **64-lane wave 原生布局** | llama.cpp fork "Native 64-thread wavefront support (vs 32-thread warps)" | wave64 | **部分已有**：`native_mmvq.cu:2343`「AMD (wave64) layout: one wavefront per R rows… 64 lanes exactly」、`router_top10.cu:191`、`qsa_decode_attn.cu:825` 硬门 `gfx906 && warpSize==64`、`iq_kernels.cu:5554`。**但 `fused_gr.cu:3101` 硬拒** `prop.warpSize != 32` | **中**（要逐 kernel 重写） | `fused_gr.cu`（HC 占 16.6%）、`sampler.cu`/`s2_expert_grouped.cu`/`qsa_select.cu` 的 32-lane 段 |
| 6 | Q8 KV FlashAttention tile | KI `fattn-q8.cuh`（`int8_t Q_values` + `half Q_scales` + `K_row_padding`） | OK | **已有** `kv_q8.cu` | 已具备 | — |
| 7 | GEMM autotuner | skyne98 `gemm-gfx906-autotuner.cuh` | OK | **已有等效物**：`STRATA_ROCBLAS_TUNING` + `gfx906-rocblas-5.5.0.txt`（W830 修回 W793 后生效，常数项 −275 ms） | 已具备 | — |

### 一句话总结这张表

**不是"从零移植"，是"补三处具体空白 + 打通一处硬门"**：
作者显然在 gfx906 上做过大量工作（有 wave64 分支、有 DPP 的局部应用、有 LDS padding 的个例、有 rocBLAS 表），
但 **① LDS padding 只用了 2 处、② DPP 只用在 1 条路径、③ fp16 dot2 一处没用、④ HC 的 persist 路径在 wave64 上被硬关**。

---

## 4 "别的架构的优化能不能扩展到 gfx906"

### 4.1 已经实测过的负面结果（省得重做）

`arch_defaults.cpp` 里 gfx906 是**空表**（P207），上游为 gfx1151 集显开的 19 项里我们测过 5 项（全 ±1.5%）、
最近把剩下 10 项**一次性全开** → `non-finite logits (#879) at position 1953`，引擎取消请求并丢弃会话（P212）。

⇒ **"打开别人架构的开关"这条路是死的**，而且不是配置问题：那些开关背后的 kernel 是按 gfx11 的指令和 wave 形态写的。

### 4.2 正确的分类法（决定"能不能扩展"）

| 类别 | 判据 | 结论 | 例子 |
|---|---|---|---|
| **A 纯算法/布局** | 只依赖内存层次与线程映射，不依赖特定 ISA | **可扩展**，与架构无关 | LDS padding、tile 划分、K-split 与否、prefetch 深度 |
| **B 需要 wave 级 primitive** | 需要 `ds_*` / `dpp` / 小范围 shuffle | **可重写**：gfx906 有全部 GFX9 primitive | DPP 归约、bpermute、寄存器分块 |
| **C 需要专用矩阵单元** | MFMA / WMMA / bf16 / FP8 | **不可扩展**（汇编器实测 `NO`） | gfx1151 那 10 项里依赖 wmma 的部分、`#4119 SELECT_TWO_PASS` 的 `qsa_block_scores_tc`（sm_80+ 张量核） |

⇒ owner 没有这张卡，所以他在 `arch_defaults.cpp` 里留空是正确的保守做法。
**我们该做的不是"帮他打开"，而是给他一份 gfx906 的 `arch_defaults` 条目 + 对应 kernel 的 gfx906 实现**——这是可以直接提 PR 的东西。

---

## 5 预期收益（用我们自己的相位表算，不外推）

`STRATA_DECODE_TIMING` 实测 **44.98 ms/窗口**（W828 §6.12 逐 kernel 分解）：

| 组成 | ms/窗口 | 占比 | 本方案能不能碰到 |
|---|---:|---:|---|
| 专家 VRAM 读取 | 10.51 | 23.4% | ✗（带宽，已 ~300 GB/s） |
| **超连接 hc0/hc1** | **7.46** | **16.6%** | ✓ 第 5 项（wave64 硬门） |
| **GDN 主体** | **7.01** | **15.6%** | ✓ 第 3 项（q8 gemv 2.44 已是 dp4a 不动；z/out-proj/rec/ab 可 dot2） |
| 各类等待 | 6.50 | 14.5% | ✗ |
| **QSA 主体** | **5.88** | **13.1%** | ✓ 第 2/3 项（attention 1.78、out-proj 0.60） |
| **router** | **3.84** | **8.5%** | ✓ 第 2 项（3 处归约循环） |
| shared expert + 量化 | 2.04 | 4.5% | 部分 |
| head | 1.73 | 3.8% | 部分 |

**可触及量 ≈ 24.19 ms（53.8%）**（AUDIT13 更正：原写 33 ms / 73%，把标 ✗ 的 6.50 ms 等待也算了进去；表中 ✓ 项只有 7.46+7.01+5.88+3.84）。若各项拿到 30–50% 局部改善，**合计 −16% ~ −27%**（原文写 −5~−10%，与自表差 3–5 倍）；
这比历史上任何"开关类"优化（一律 ±1.5%）大一个档次，因为它是**算术吞吐翻倍**，不是省 launch。

---

## 6 执行顺序（按 可判性 ÷ 成本）

### 第 0 步：微基准先行（不停服，~30 min）

三条手法都能先在**独立微基准**里量，不碰生产：
`LDS 列式读带宽（ld=32 vs 33）`、`DPP vs bpermute 归约（512→10 top-k 形状）`、`fdot2 vs f32-fma 点积（K=2048/4096）`。
**先证明 gfx906 上的倍数与我们读到的一致**，再改引擎——否则又是一次"照别人的数拍脑袋"。

### 第 1 步：`native_router.cu` 的 DPP 归约（最小改动）

- 3 处：`native_router.cu:36`（和）、`:41`（max）、`:82/:136/:193`（argmax 双值）
- 现写法 `__shfl_xor_sync(0xffffffffu, v, mask, 32)`，在 wave64 上走 `ds_bpermute_b32`
- 改成 `__builtin_amdgcn_mov_dpp`（`qsa_decode_attn.cu:478` 已有现成写法可抄）
- 另：`route_resident_k<<<n_tok, 32>>>` 每块只有 **32 线程 = 半个 wave64**（`:324`），值得一并评估
- 判据：`ms/win`（router 现 3.84 ms），一次 A/B 约 12 min

### 第 2 步：LDS +1 padding 系统化（零风险）

- `qsa_decode_attn.cu:138-140`（`sq[G][HD]`、`sp[G][CHUNK]`）、`:354-356`（`spt[CHUNK][G]`，**cell-major 正是列式消费**）
- `qsa_select.cu` 其余 `so` 变体
- 只改声明与索引，不改算法；判据同上

### 第 3 步：`fused_gdn.cu` 的 fp16 路径换 dot2（要过精度门）

- 现状 `:115-118`：`fmaf(__uint_as_float(wv.x << 16), xa.x, acc)` —— 这是 **bf16→fp32 的位拼接**，不是 fp16
- 若改成 `__ockl_fdot2`，必须先把权重转成 **fp16**，而 **bf16→fp16 会丢指数范围**（fp16 5 位指数 vs bf16 8 位）
- ⇒ **必须先跑 KL 门**（我们已有 `kl_prop` 管线，地板精确为 0，见 P213）。这是唯一有数值风险的项。

### 第 4 步：`fused_gr.cu` 的 wave64 通道（工作量最大）

- `:3101` 硬门 `prop.warpSize != 32` → 直接关掉 `STRATA_HC_PERSIST`
- 该路径注释写"written and measured for gfx1030"，HC 占 16.6%，是最大单块
- 需重写 32-lane 布局为 64-lane（`fused_gr.cu` 里 `tid&31` 27 处、`/32` 20 处、`>>5` 26 处）

---

## 7 必须诚实说的局限

1. **llama.cpp 那条线拿不到源码**：166 上只有二进制镜像，代码结构（ggml）与 Strata 不共享任何层，**只能搬手法**。
2. **第 3 步有真实数值代价**：bf16→fp16 是**换档**，不是等价的加速。参考 P197 的结论，我们已经在"质量/字节"拐点上，这条要么过 KL 门、要么放弃。
3. **第 4 步工作量以周计**：`fused_gr.cu` 是 3100+ 行、大量手写寄存器布局，重写风险高。
4. **收益是"局部 2×、全局 5–10%"**：因为分母分散（最大单项 23.4% 还是纯带宽，碰不到）。任何声称"移植后翻倍"的说法都不成立。
5. **本轮全部是判断，没有一行代码改动，生产未动。**

---

## 8 数据出处

| 结论 | 出处 |
|---|---|
| 指令可用性 | 本轮实跑 `/opt/rocm/llvm/bin/llvm-mc -mcpu=gfx906`（见 §1 表），166 上执行 |
| LDS padding 2.13× | skyne98 wiki `gfx906-lds-layout-standard-llm`（`ds_read_b128` 列式 1865→3974 GB/s） |
| dp4a / dot2 可用 | skyne98 `gfx906-special-isa-quant-dequant` 独立复验，与本轮一致 |
| KI 手法 | `csrc/rocm/dense_gemv_gfx906.cu`（`__ockl_fdot2`、`atomic_add_pk2_f16`、K-split 被证伪）、`csrc/gfx906_fa/kernel/fattn-q8.cuh`、`gfx906-config.h` |
| llama.cpp fork 手法 | `eslowney/llama.cpp-gfx906`、`fuutott/llama.cpp-gfx906` README（DPP reductions、Q8 FA tile、64-thread wavefront、gfx906 vectorized loads） |
| Strata 现状计数 | 本轮 `grep` 全库 49 个 `.cu`（`__shfl_xor` 193/31 文件、`__ockl_fdot2` 0、`dpp` 2、`&31` 178、`>>5` 198、`/32` 280） |
| 相位权重 | `W828_UPSTREAM_028_PORT.md` §6.12（44.98 ms/窗口逐 kernel） |
| gfx1151 十项算 NaN | P212 / `W832_OPT_PLAN_V2.md` §4.3 |
| MMQ_KQ 值 +68% | P198 |

---

## 9 上游侦察（2026-10-31，本节修正 §3/§5 的结论）

> 起因：§1–§8 只看了 166 本地树。**本地不是最新**——KI 停在 `6ccbb03`（2026-09-27），
> 上游已是 `3857591d`（2026-10-26），**落后 1209 个 commit**。本节是补齐后的结果，
> 并且**推翻了 §3/§5 的三条判断**。

### 9.1 上游现状（GitHub API 实测，2026-10-31）

| 项目 | 本地 | 上游 HEAD | 落后 | 说明 |
|---|---|---|---|---|
| **KIntegrated/vllm-gfx906-mobydick** | `6ccbb03`（09-27） | **`3857591d`（10-26）** | **1209 commits** | 59 条 gfx906 相关提交，`docs/gfx906/` 有整套 DEVLOG |
| ggml-org/llama.cpp | `3cf0325`（Strata 内置） | `0ec4027a`（10-31） | — | gfx906 无系统性支持 |
| iacopPBK/llama.cpp-gfx906 | — | `125db33d`（08-22） | — | fork 主力之一 |
| fuutott/llama.cpp-gfx906 | — | `89315ff0`（2025-11-24, v6） | — | DPP + Q8 FA |
| eslowney/llama.cpp-gfx906 | — | `c0c5f68f`（2025-09-08） | — | D=128 FA |
| Niko1221/Strata | `0.2.8` | `870aedd9`（10-29） | 0 | 我们已最新 |

### 9.2 修正一：§3 第 3 项（`v_dot2` 换 ALU）在 **gather 型** 路径上无效

KI 的 `DEAD-ENDS.md` 有一条**做过并被否掉**的实验，与我们 §3 第 3 项是同一件事：

```
salvage LEGACY=0 via a better dot instruction (dp4a/dot2/dot8 swap in the KQ loop)
  Gate: ISA rate probe + roofline (analytic)
  VERDICT: DEAD-END (analysis)
  「dp4a/v_dot4_i32_i8 already the inner loop and measured FULL-RATE
    (4.44× fp32, 2× packed fp16); B=1 decode is gather-HBM-bound ~2.7×
    so ALU swaps can't surface」
```

**⇒ 对"gather 型"kernel（专家读取、FA 的 KV gather），ALU 已满速，换指令不动结果。**

但**不能因此否掉我们的全部候选**：我们的 GDN/QSA-score 是 **dense GEMV**（读连续权重行，不是 gather），
机理不同。**判据不是"别人说无效"，而是先做 roofline**——这正是 KI 用的方法（ISA rate probe + roofline）。

§5 里我写的"若各项拿到 30–50% 局部改善 ⇒ −5~−10%"**没有区分 gather / dense**，过粗，作废。

### 9.3 修正二：真正的杠杆在**字节侧**，不在 ALU 侧

KI 的 `T1` 条目（PROBE GO）：

```
T1: int8 (W8A16) the unquantized BF16 weight mass —
    lm_head, FA q/k/v, GDN in_proj/out_proj, shared expert, layer 0, the BF16 MTP draft layer
  Probe: 1.93× at lm_head (1717 µs vs the recorded 3114–3193 µs floor)
         2.00–2.42× at the other floor-bound shapes, ≥0.96× everywhere
  Ceiling: dense +10–13 %, MoE +14–19 %
```

**这正是我们 decode 相位表里"未量化的那一半"**：

| 我们的组成 | ms/窗口 | 占比 | 是否已量化 |
|---|---:|---:|---|
| 专家读取 | 10.51 | 23.4% | ✅ Q4_K/Q5_1 |
| HC `hc0/hc1` | 7.46 | 16.6% | ✅ `HC_Q8=1` |
| GDN：`q8 gemv` 2.44 | 2.44 | 5.4% | ✅ dp4a |
| **GDN：z 1.55 / out-proj 1.62 / rec 0.67 / ab 0.52** | **4.36** | **9.7%** | ❌ fp16/bf16 |
| **QSA：q 1.67 / attention 1.78 / out-proj 0.60** | **4.05** | **9.0%** | ❌ |
| **router** | **3.84** | **8.5%** | ❌ |
| **head** | **1.73** | **3.8%** | ❌ |

⇒ **未量化约 14 ms / 窗口（31%）**，形状与 KI 的 T1 清单高度重合（lm_head / q/k/v / GDN in_proj/out_proj）。

**但有一条必须同时记住的反例**：KI 的 `T-1`（把同一手法用到 drafter 的 fp16 mass）**最终 NOT PASS**
——"final k=4 re-test parity −1 %；**earlier +15–18 % was a cold-start misread**"。
⇒ **probe GO ≠ serving GO**。这条与我们自己的 P200（不许外推）是同一条纪律。

### 9.4 修正三：同模型（Qwen3.8-Flash-Next / QSA）的实测底账

KI 服务的**就是我们的模型**（`qwen4_exp` QSA + PLE + GDN + hyper-connections）。它的 RECON 给了 ISA 级事实：

| dtype 组合 | gfx906 实际发出的指令 | 每 32 MAC 的指令数 |
|---|---|---:|
| fp16 × fp16 → fp32 | `v_dot2_f32_f16` | **32** |
| **bf16 × bf16 → fp32** | **标量 `v_fmac_f32`（无 bf16 指令，靠 upcast）** | **60** |
| int8 × int8 → int32 | `v_dot4_i32_i8`（+`v_perm_b32` 打包） | **16** |

实测：**QSA kernel pair 在 fp16 下 26.5 ms，bf16 下 116.5 ms = **4.40×****（`±0.2%`）。

**我们的位置**：生产已 `STRATA_HIP_PROMPT_F16=1`，走 fp16 ⇒ **这 4.40× 我们已经吃到了**。
但这条同时说明：**任何把 QSA 往 bf16 推的改动都是灾难**（gfx906 上没有 bf16 指令）。

**tiled indexer**：KI 实测 fp16 下 **1.39×（kernel）/+39%**，bf16 下 **0.42×（灾难）**，必须按 dtype 门控。
⇒ 我们的 `native_qsa_indexer.cu` 是否已 tiled，是一条**可直接对照的待查项**。

**int8 KV**：KI 实测在 gfx906 上 **attention prefill 慢 2.5–2.7×，decode 中性**，只买容量。
⇒ 我们用 `--kv k8v4`，**需要核对是否付了同样的 prefill 代价**（这是本轮新提出、尚未测的项）。

### 9.5 llama.cpp 这条线：上游是零散支持，不是系统支持

| PR | 状态 | 内容 | 对我们的意义 |
|---|---|---|---|
| **#15927** | **MERGED** 2025-09-11 | `CUDA: larger SRAM reads for tile FA, AMD FP16 dot`：SRAM 读 8/16 B，FP32→FP16 转换前置；作者原话「`v_dot2_f32_f16` ... available everywhere except for RDNA 1」 | **独立印证 §1 的汇编器结论**；我们的 `PROMPT_F16` 同源 |
| **#16291** | **closed，未合并** | `hip: substituted bpermute ops with swizzle ops (gfx906, maybe all AMD)`，实测 **+20% 平均** | **这正是我们 `STRATA_GFX906_ATTN_QUERY_SWIZZLE` 在做的事**；上游搁置 ⇒ gfx906 只能靠 fork |
| #29427 | open | 把 gfx1012 加进 `V_DOT2_F32_F16_AVAILABLE` | 说明 ggml 有**逐架构白名单**，gfx906 在不在里面要看宏定义 |
| #30336 | open | 把 gfx906 加进 `hip-quality-check.yml` | CI 覆盖，与性能无关 |

**结论不变但更硬**：llama.cpp 与 Strata 是**平行的两套实现**，共享的只有"手法"。
但 `#16291` 与我们的 `GFX906_ATTN_QUERY_SWIZZLE` 独立得到同一结论（bpermute → swizzle/DPP，+20%），
**这是双向确认**：这条路是对的，且我们已经在上面。

### 9.6 顺带查到的：Strata 上游有 3 个我们该跟的条目

| 条目 | 状态 | 与我们什么关系 |
|---|---|---|
| **#3986** `gfx906: fix the build of src/core/dflash2.cpp` | open | **就是我们的 W776**（只给该文件加 `STRATA_USE_HIP`）。有人在做同一件事 |
| **#4766** `gfx906: build dflash2 for Radeon VII` | open | 同上，**两个 PR 撞车** |
| **#3073** `STRATA_SELECT_SIMT=2 takes the simt2 scorer on HIP too` | open | 我们只用了 `=1`，**`=2` 是新取值，未测** |
| **#4781** `0.1.54 prompt rate drop on a 20 GB Ada card: the auto expert cache is to blame` | open | 0.1.54 的 prompt 回归，指向 auto expert cache；**我们的 `--expert-cache auto` 值得核对** |
| #4616 | open | 社区 MI50 (gfx906) benchmark 报告 |
| #4159 | closed | `MI50: prompt speed with STRATA_HIP_PROMPT_F16` —— 我们这条路的公开记录 |

### 9.7 修正后的可执行顺序（取代 §6）

| 序 | 动作 | 为什么排这里 | 成本 |
|---|---|---|---|
| **0** | **roofline 判定**：对 `fused_gdn` / `native_qsa_score` / `native_router` 各做 ISA rate probe（实测该 kernel 达到 fp32-FMA 记录的百分比） | **这是 §9.2 的直接产物**：ALU 已满速的话换 dot2 就是白干。KI 用这个方法否掉了自己的一条假设 | 不停服，~40 min |
| **1** | **T1 同型**：找出我们"未量化的 14 ms"里哪些是 floor-bound，做 int8 W8A16 探针 | KI 探针 1.93×，但我们自己的 T-1 反例说明**必须过 serving gate** | 探针 ~1 h |
| **2** | `native_qsa_indexer.cu` 对照 KI 的 tiled 路线 | 有现成的 1.39× 先例，fp16 门控 | 小 |
| **3** | 核对 `--kv k8v4` 的 prefill 代价 | KI 说 int8 KV prefill 慢 2.5–2.7× | 一次 A/B |
| **4** | `--spec-min-p`/ALU 换指令一类 | **已被 §9.2 降级**，只在前 3 项做完且仍有缺口时才碰 | — |

### 9.8 一条方法学纪律（从 KI 的 DEAD-ENDS 抄，写进我们的规矩）

KI 的 "recurring lessons" 三条，与我们踩过的坑逐条对应：

1. **standalone harness 的赢不会迁移到 serving wall-clock**（它们的 profiler/launch regime 与 serving 不同）
   ⇒ 对应我们 P200。
2. **serving graph A/B 才是 µs 级判决的 gate**；eager A/B 会在 launch-bound 时给出平局
   ⇒ 我们的 6% 噪声底盘正说明这一点，必须用**同实例内交替 + 每臂 n≥20**。
3. **PPL / prompt_logprobs 在 hybrid attention 上不可靠**，要用"文本连贯 + logprob A/B"
   ⇒ 我们用 KL 门是对的，但要同时看文本。

---

## 10 Strata **自身**能扩展到 gfx906 的部分（源码级，2026-10-31）

> 问题：不是"别人→Strata"，而是 **Strata 内部为别的架构做的事，哪些能延伸到 gfx906**。
> 关键提醒（机主）：**"有分支"不等于"那条路已经优化到底"，尤其近期优化项。**

### 10.1 结构性事实：gfx906 连入口都没有

`src/core/arch_defaults.cpp:25-93` 的全部逻辑：

```cpp
arch_default_env(gcn_arch, defaults026, windows) {
    if (gfx_arch_is_gfx12(...))  { ...RDNA4 表（9 项）... }
    if (!gfx_arch_is_gfx1151(...)) return t;   // ← gfx906 在这里 return 空表
    ...gfx1151 表（19 项）...
}
```

全库只有 **4 个架构谓词**：`gfx12` / `gfx12_wmma` / `gfx11_wmma` / `gfx1151`（`grep gfx_arch_is_` 计数 16/3/9/5）。
**没有 `gfx906` 谓词**——gfx906 的识别全靠在业务代码里写字符串 `gfx_arch_is(arch,"gfx906")`。

按文件看"谁有别的架构分支、gfx906 零分支"（`grep -c` 计数）：

| 文件 | gfx906 | gfx11x | gfx12 | 判定 |
|---|---:|---:|---:|---|
| `prefill/kernels.cu` | **0** | 23 | 3 | GDN chunked recurrence 只有 gfx11 WMMA 版 |
| `prefill/wmma_gemm.cu` | **0** | 23 | 0 | WMMA 专用，不可移植 |
| `kernels/cuda/qsa_select.cu` | **0** | 14 | 15 | scorer 走 `v_wmma_f32_16x16x16_bf16`，不可移植 |
| `prefill/gemm.cu` / `prefill.cpp` | 0 | 4/7 | 3/3 | 见 §10.3 |
| `kernels/cuda/qsa_decode_attn.cu` | **15** | 0 | 0 | ← decode 侧做过（`reduce12_gfx906`、swizzle） |
| `fused_gr.cu` | 7 | 4 | 8 | 混合 |
| `iq_kernels.cu` | 5 | 7 | 4 | 混合 |

### 10.2 【最高价值】四个 opt-in 开关：kernel 无架构门控，但 gfx906 进不了表

这四项**不在**我们任何一次实验里（P212 那 10 项只含 `TSUM`，不含另外三项），而 gfx12 表实测**四项一起 +3.5% 且 md5 与默认相同（bitwise）**：

| 开关 | 读取点 | 源码原话 | 打在我们哪 |
|---|---|---|---|
| **`STRATA_ATTN_LANECELL=1`** | `qsa_decode_attn.cu:916`, `:1161` | S25：score phase **one cell per thread（bit-identical scores, no shuffle reductions）** | **QSA decode attention（13.1%）** |
| **`STRATA_ATTN_MERGE_V2=1`** | `qsa_decode_attn.cu:929` | 1 用 `attn_merge_v2_kernel` | 同上，merge 相 |
| **`STRATA_EXPDEC=1`** | `iq_kernels.cu:2432` | 组激活的窗口 kernel（`STRATA_EXPDEC_MINBLK` 控制 in-flight block） | 专家 decode |
| **`STRATA_TSUM=1`** | `fused_gr.cu:2259`, `iq_kernels.cu:6270` | S26：**one transposed butterfly per warp（bitwise the same values）** | **HC/GR（16.6%）+ 专家** |

gfx12 表里这四项的单独读数：`ATTN_LANECELL + ATTN_MERGE_V2 = +1.9%`、`TSUM +1.9%`、`EXPDEC +0.6%`，四项合计 **+3.5%（3/3 对，md5 相同）**。

**gfx906 为什么拿不到**：它们是 `arch_defaults` 里的表项，而 gfx906 在 `if (!gfx_arch_is_gfx1151) return t` 处就返回了。
**kernel 侧没有任何 gfx906 排除**——四条读取点都是纯 `getenv`。
⇒ **这四项是"纯实现缺口"，且两条自证 bit-identical / bitwise。**

### 10.3 【纯实现缺口】别的架构有、gfx906 明确没有的

| 项 | 证据 | gfx906 现状 | 可移植性 |
|---|---|---|---|
| **`STRATA_HC_UPMIX`**（HC read 的 up-projection + epilogue 融合） | `prefill/kernels.cu:2295`「opt-in, **gfx11**」+ `:2367`「**sm_80+**」；`prefill.cpp:461`「gr_upmix: gfx11」 | **无 gfx906 版** | **纯算子融合，无架构指令依赖 ⇒ 可写 gfx906 版**（属 **prefill** 路径） |
| **`STRATA_GDN_CHUNKED`**（WY 形式的分块 recurrence） | `prefill/kernels.cu:1675` `#if defined(__gfx1100__)...__gfx1151__` → `STRATA_GDN_WMMA`；`:1692` `__builtin_amdgcn_wmma_f32_16x16x16_f16_w32` | **无** | **算法可移植，指令不可**：chunked scan 本身不用 WMMA，可用 fp32/VGPR 重写（属 **prefill**） |
| **`STRATA_GRAPH_PRIO`** | `src/core/verify.cpp:219` 逐字 `#if defined(STRATA_USE_HIP) \|\| defined(STRATA_HIP_GFX906) \|\| defined(STRATA_GPU_METAL) return false;`，注释「every HIP caller is guarded off」 | **硬关** | **纯缺口**：HIP 完全支持流优先级。属 spec-decode 的 verify window graph |
| conversation checkpoint / park 异步族（`STRATA_CKPT_ASYNC` / `PARK_ASYNC` / `CKPT_POOL` / `CKPT_GATHER` / `PARK_VRAM_MIB`） | 上游 `#3779` 正文逐字：「The conversation-cache copy paths and `GRAPH_PRIO` are **CUDA only. On HIP, gfx906 and Metal they are off.**」 | **无** | **纯缺口**（host 内存/拷贝线程管理），与计算架构无关 |

### 10.4 明确**不可**移植（硬件，有汇编器或源码双证）

| 项 | 判据 |
|---|---|
| `qsa_select.cu` 的 gfx11/gfx12 scorer | `v_wmma_f32_16x16x16_bf16_w32` / `_gfx12`；gfx906 **无 WMMA**（`llvm-mc` 判 `v_mfma` NO，WMMA 属 gfx11+） |
| `STRATA_GDN_TC` | tensor-core scan（`gdn_tc.cuh`），需 sm_80+ / MFMA |
| `STRATA_PF_FUSED_F16` / `PF_FUSED_WS` | f16 mma fused experts，源码注「sm_80+ only」 |
| **`STRATA_DEQUANT_WIDE`** | **看似最像"纯赚"但实际不适用**：`dequant_bf16.cu:293` 按 CUDA compute capability（6.1 / 8.6 / 8.0）判，gfx906 走 HIP 恒 OFF；**但**我们的 prefill 是 `MMQ_KQ=1` ⇒ `prefill.cpp:1836 if (mmq_plan().any)` 走 MMQ，**不解包成 bf16**，那条 dequant 路径用不上。⇒ 收益接近 0，**不列为候选** |

### 10.5 结论：gfx906 的缺口分三类，只有两类值得做

| 类 | 判据 | 数量 | 处置 |
|---|---|---|---|
| **A 纯实现缺口**（别的架构有、无指令依赖） | 源码里只有 CUDA/gfx11/gfx12 分支，无 ISA 理由 | 4 项开关 + HC_UPMIX + GDN_CHUNKED(算法) + CKPT/PARK 族 | **可做，优先级最高**（A 类里 `LANECELL`/`TSUM` 已自证 bitwise） |
| **B 硬件不符** | 依赖 WMMA / MFMA / tensor core / bf16 | WMMA scorer、GDN_TC、PF_FUSED_F16 | **不做** |
| **C 路径不适用** | 功能存在但不走我们这条路 | `DEQUANT_WIDE`（我们走 MMQ） | **不做** |

### 10.6 这一节对"owner 没有这张卡"的意义

`#3779` 的处境与我们**逐字相同**：*“sm_80 has no entry in the engine's per-card tables, so on a GA100 card most of the prompt and decode path runs on choices made for other architectures.”*
社区为 sm_80 补了 13 个开关（其中 2 个默认开、bitwise），换到 **prompt 2.0× / decode +20%**。

⇒ 我们该产出的不是"帮 gfx906 打开表"，而是 **一份 `gfx906` 的 `arch_default_env` 条目 + 每个"Rounding-level / bitwise"标注的实测依据**——这正是可以提 PR 的形状，也是 owner 在没有这张卡的情况下最需要的东西。

---

## 11 实测：那四个"别的架构上 bitwise 有收益"的开关，在 gfx906 上是**负的**

> 这是 §10.2 的直接验证。5 臂，每臂 8×128 tok decode + 3 档 read，**base 与 base2 复测**。

### 11.1 结果

| 臂 | env 增量 | decode 中位 (tok/s) | read 1958 | read 3718 | **read 6666** |
|---|---|---:|---:|---:|---:|
| **base** | — | 51.65 | 4052 | 6121 | **9707** |
| **base2**（复测） | — | 51.70 | 4103 | 6042 | **9708** |
| **tL** | `+ATTN_LANECELL=1` | 51.60 | 4117 | 6234 | **10156（+4.6%）** |
| **tLT** | `+TSUM=1` | 51.60 | 4134 | 6231 | **10199（+5.1%）** |
| **tL4** | `+ATTN_MERGE_V2 +EXPDEC` | 51.70 | 4088 | 6185 | **10123（+4.3%）** |

- **复现性**：base vs base2 的 read 6666 是 **9707 / 9708（差 0.01%）**，decode 51.65/51.70（0.1%）⇒ 这次的对照极稳。
- **decode：四项全部零收益**（51.60–51.70，噪声内）。
- **prefill：一致退化 4–5%**，且 **`tL` 一项就已退化**，再加另外三项没有进一步变化（10156 → 10199 → 10123）
  ⇒ **退化由 `STRATA_ATTN_LANECELL` 单项造成**，不是叠加效应。
- 三个长度都退化（1958: +1~2%、3718: +2~3%、6666: +4.3~5.1%），**随长度放大** ⇒ 是 attention 相位的真实成本，不是噪声。

### 11.2 判词

**四项全部不采用，生产不变。**

对照 gfx12（RDNA4）表里写的 `ATTN_LANECELL + ATTN_MERGE_V2 = +1.9%`、`TSUM +1.9%`、`EXPDEC +0.6%`、四项合计 **+3.5%（bitwise）**：
**同一批开关在 gfx906 上是 0（decode）/ −4.5%（prefill）**。

### 11.3 这条负结果值什么

1. **"别的架构的表不能照搬"有了本机实证**。此前 §4.1 的 gfx1151 十项是"数值崩"（non-finite），
   这次是"数值对但变慢"——**两种失败模式都出现了**，后者更隐蔽（不报错、答案一致，只是慢）。
2. **`arch_defaults` 的每一行都是按那张卡实测的**，不是可推导的。所以"给 gfx906 补表"这件事，
   **只能靠在本机逐项实测，不能从 gfx1151/gfx12 的表推**。
3. **§10.2 把 LANECELL 列为"最高价值候选"是错的**，理由是我只看了源码注释里"bit-identical"和
   gfx12 的 +1.9%，没有 gfx906 的证据。**"bit-identical"只保证答案不变，不保证不变慢。**
   ⇒ 新增纪律：**任何来自别的架构的开关，在 gfx906 上一律按"未知"处理，先单项测，禁用叠加测**。

