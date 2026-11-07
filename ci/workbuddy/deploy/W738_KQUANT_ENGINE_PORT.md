# W738 三问：K-quant 要不要补 / ki 的 custom 引擎有没有用 / ki 还有什么可借鉴

> 触发：机主三问 -- 「k quant量化补起来有用吗？ki的custom引擎有用吗？ki的项目还有什么可以借鉴的？」
> 基线：Strata **0.1.41** 生产容器 `strata166-407`（源码走 `docker exec` 读容器内 `/src`，与宿主 `/home/albus/strata166/build-ctx-411` 同源）；
> routeK 主源 = `166:/home/albus/routeK/src`（**按 W737 的教训，本轮 routeK 侧一律读它的树，不读归档件**）。
> 证据等级：**[Strata源码]** / **[Strata文档]** / **[routeK源码]** / **[routeK实测]** / **[推测]**。
> **本轮只读**：未发车、未改参数、未动生产；166 上只读。

---

## §0 三问速答

| 问 | 答 | 一句话依据 |
|---|---|---|
| **K-quant 补起来有用吗** | **不用补 -- 上游已经补了**；而我们**自己那条该开的、按位等价的流从没开过** | `iq_kernels.cu:3473` 逐字注释：`stream B: UD-Q4_K_XL's Q4_K / Q5_K gate/up and Q5_1 / Q8_0 down` => K-quant 的专用流 `STRATA_EXPERT_V2K`（`s27_launch_ts`）**已在树里**；而我们的 pack 对应的是 `STRATA_EXPERT_V2`（`s26_launch_l`），**两者都默认关，我们的 env 里一个都没设** |
| **ki 的 custom 引擎有用吗** | **引擎本身不可用**（吃不了我们的权重、绑定 torch/vLLM）；**它的结论与工具可用** | 它的 gfx906 内核是 **torch 扩展**（`#include <torch/all.h>`），量化契约是 **AWQ/GPTQ W4A16 + fp16 激活**，dot 走 `__ockl_fdot2`；routeK 的 vLLM 里含 `gguf` 的文件**只有 1 个** |
| **ki 还有什么可借鉴** | **89 份 `docs/gfx906/`** 里约有 **12 类**可直接用（排除台账 / ROADMAP / DVFS / PCIe-ACS / 服务态 bench / 256k OOM / 主机态退化 / 逐 step 账 / GDN / int8 台账 / RECON / 卡死诊断） | 见 §4 逐条 |

**本波最大的一条不在三问里**：上游为 **gfx1151（Strix Halo）** 打包了一整族「**默认开、按位等价**」的开关
（`STRATA_EXPERT_V2` / `TSUM` / `LFUSE` / `QFUSE` / `SH_STREAM` / `Q8_PACKED` / `GDN_*` / ...），
**gfx906 上它们全关**，而我们的 `PARAM_REGISTER.tsv`（50 行）**一个都没有登记**。见 §2。

---

## §1 第一问：K-quant 补起来有用吗

### 1.1 我们那个 pack 到底是什么量化（先钉死，别再猜）

`/data/packs/huihui-ud-iq4_xs/native_experts.txt` 头两行逐字：

```
# strata native experts v4: layer gu_type d_type offset blob_bytes gate_off up_off down_off [...] (n_expert 512, total 59519795200; ...)
0 21 20 0 2329600 30522232864 30889674784 30048632864 Qwen3.8-Flash-Next-UD-IQ4_XS-00002-of-00003.gguf
2 23 8 2385510400 3481600 33536747296 33989386016 32643716896 ...
4 21 8 5360844800 3148800 ...                                   <- 少数层
```

类型 ID 的映射**从源码取**（不信记忆）：`include/strata/kernels/dequant_bf16.hpp:6` 逐字
「IQ4_NL **(20)**, IQ4_XS **(23)** and Q2_0 **(42)**」；`native_mmvq.hpp:7` 列出 `Q2_0, Q4_0, Q5_0, Q8_0, Q3_K, Q4_K, Q5_K, Q6_K, IQ4_NL`。
=> **21 = IQ3_S，20 = IQ4_NL，23 = IQ4_XS，8 = Q8_0**。

-> 我们的专家张量：**48 层里 44 层是 `IQ3_S gate/up + IQ4_NL down`**，4 层是 `IQ4_XS gate/up + Q8_0 down`。
**一个 K-quant 都没有**（12=Q4_K / 13=Q5_K / 14=Q6_K 零命中）。

形状也能**算术闭死**（我按 ggml 块大小反推，两处**恰好相等**）：

| 层型 | 算式 | 与 `blob_bytes` |
|---|---|---|
| `gu 21 / d 20` | 2 x 640 x (2560/256) x 110 + 2560 x (640/32) x 18 = **2,329,600** | 2,329,600 **恰等** |
| `gu 23 / d 8` | 2 x 640 x 10 x 136 + 2560 x 20 x 34 = **3,481,600** | 3,481,600 **恰等** |

-> **n_embd = 2560，n_ff = 640**（不是推测，两处逐字节吻合）。

### 1.2 引擎对这两条路各有什么（判据在源码里）

`src/kernels/cuda/iq_kernels.cu`：

```c
static const bool v2 = getenv("STRATA_EXPERT_V2") == "1";
if (v2 && L.gu_type == 21 && L.d_type == 20 && L.n_embd == 2560 && L.n_ff == 640) {   // S26: see s26_gu_l_kernel
    ... s26_launch_l<...>(...) ...  return;
}
// stream B: UD-Q4_K_XL's Q4_K / Q5_K gate/up and Q5_1 / Q8_0 down (see S27 above)
static const bool v2k = getenv("STRATA_EXPERT_V2K") == "1";
if (v2k && (L.gu_type == 12 || L.gu_type == 13) && (L.d_type == 7 || L.d_type == 8) &&
    L.n_embd == 2560 && L.n_ff == 640) {
    ... s27_launch_ts<G, D>(...) ...  return;
}
```

- **K-quant 那条（`V2K` / `s27`）已经存在**，且注释写明它服务的就是 **Unsloth `UD-Q4_K_XL`** 这一个 pack。
- 我们那条（`V2` / `s26`）段头逐字（`iq_kernels.cu:2005-2008`）：
  「**S26 `STRATA_EXPERT_V2=1` (opt-in): IQ3_S gate/up + IQ4_NL down** / **Bitwise equal** to native_gu_multi_kernel /
  native_down_multi_kernel (**S26 harness, real UD-IQ4_XS expert blobs, T 1-3, memcmp of every output**):
  each row's lane sums and warp_sum are the same; a warp interleaves RPW rows (**more loads in flight**) and reads the
  chunk's activation rows from LDS and, for IQ3_S, the grid table from LDS (the same values).」
- 另有子开关 `STRATA_TSUM`（同一段加注释）：down rows 的 items 均匀铺到 lane、一组 load，
  **harness 1.09-1.12x vs 1.03-1.06x**；而**对 gate/up 同样做法是 0.6-0.8x**（=> 子开关对 gate/up 有害，只该用于 down）。

### 1.3 结论（三问之第一问）

1. **「补 K-quant」在专家路径上不是空缺** -- `s27` 那条流就是为 `UD-Q4_K_XL` 写的，已经在树里、能编、有专用 kernel。
   -> 若我们的意思是「让引擎能吃 K-quant 权重」，**已经能吃**。
2. **但换到 K-quant 权重 = 换量化契约 = 换质量**（IQ3_S/IQ4_NL 与 Q4_K/Q5_K 的误差分布不同），
   而且**收益未知**：源码里能查到的「CUDA 布局 vs AMD 布局」对照数字**全是 V100 的**
   （`kExpFallback = 0; // ... (V100, IQ2_XXS gate/up: R2 183 us vs 113)`、`// V100-SXM2, a verify window's VRAM call: 227 -> 159 us`），
   **gfx906 上一格都没有**。
3. **真正的机会是把我们现有的那条流打开**：`STRATA_EXPERT_V2`（S26）**为 IQ3_S/IQ4_NL 而写、用真 UD-IQ4_XS blob 做过位等验证（T 1-3, memcmp of every output）、默认关、我们从未设过**。
   - 处置：**候选 R0**（零正确性风险；但**须按 routeK 的「孤岛快、进服务丢」纪律**，服务态 A/B 才算数）。
4. 若确实想走「换 K-quant 权重」：**第一步不是写内核**（已有），而是
   ① 用树的 `native_expert_bench <shard.gguf> <layer> <groups> <tokens> <ref mode> <mode>`（`src/kernels/native_expert_bench.cpp`，
   头部逐字：「the grouped native experts on **real GGUF rows**: one AMD layout against another, **bit for bit**, and each one's time」）
   在**同一台机**上量「K-quant 在 CUDA 布局下的每-expert 成本 vs IQ 在原生布局下的成本」；② 过质量门。

---

## §2 顺带查到的更大一条：整族「gfx1151 默认开、按位等价」的开关，我们一个都没登记

`docs/STRIX_HALO.md:82` 节标题逐字 **「## 4. What is on by default on gfx1151」**，正文：

> At start the engine looks at GPU 0; **on a gfx1151 it sets the switches below unless you set them yourself**
> (`STRATA_GFX1151_DEFAULTS=0` turns the whole table off, and the start-up line names what was set).
> **Every one of them gave byte-identical output on the maintainers' box** (the same token ids, 4K / 32K / 64K and four models,
> and a bitwise harness per kernel): **they change speed, not answers**. **Nothing here applies to CUDA or to another AMD architecture.**

表（节选，含与**我们直接相关**的两行）：

| 开关 | 逐字用途 |
|---|---|
| **`STRATA_EXPERT_V2`, `STRATA_TSUM`, `STRATA_LFUSE`** | **the grouped decode experts (IQ3_S / IQ4_NL)**, single-butterfly warp sums, fewer launches around the shared expert and the KV append |
| `STRATA_Q8_PACKED`, `STRATA_Q6_PACKED`, `STRATA_MMVF_ROWS`, `STRATA_ATTN_LANECELL` | decode layouts and kernels（packed Q8_0 / Q6_K weights, 4-row BF16 GEMV, one-cell-per-thread attention scores） |
| `STRATA_GDN_HEAD`, `STRATA_GDN_PP=2`, `STRATA_GDN_CONVL2`, `STRATA_GDN_NOY` | the prompt's gated-delta-net recurrence |
| `STRATA_GDN_SPLIT`, `STRATA_QFUSE`, `STRATA_PLE_BATCH` | the GDN step over four blocks per head, activation images written by their producers, the PLE key/value projections of a verify window at once |
| `STRATA_SH_STREAM=1` | the shared expert on a second stream beside the routed experts. **It is off by default on other AMD cards (#816)**, but it pays on gfx1151: **decode +1.8% (UD-IQ4_XS)** and +6.7% (UD-Q4_K_XL) at 8K |
| `STRATA_HCD_EXACT`, `STRATA_CVEC_FUSE`, `STRATA_PF_PAD` | 超连接 down 投影 / 受控层写+控制向量+下一 norm 一趟 / padded GEMM 行 stride |

同文档 `## 5. What is not on by default (it changes bits)` 给的是**另一族**（改位、需门）：
`STRATA_PF_FUSED` / `STRATA_PF_GEMM` / `STRATA_HC_UPMIX` / `STRATA_PA_FAST` / **`STRATA_HIP_WMMA`** / **`STRATA_SELECT_WMMA`**，
并逐字写明门法：「they are opt-in and the maintainers **gate them with KL against the default**
(`STRATA_PF_SWITCH_MIN_T=4096` keeps the short prompts on the default numerics)」。
=> **上游自己就用 KL 作「改位开关」的门** -- 与 routeK 的 `routek-kv-precision-ab`（KLD 为主门）**同源**；
且 §5 那几个 **WMMA** 开关在 gfx906 上**不可用**（P96：gfx906 无 WMMA/MFMA）。

**已核实的存在性与默认态（本轮实测）**：

| 检查 | 结果 |
|---|---|
| 二进制字符串 | `STRATA_GROUPED_V1` / `STRATA_EXPERT_V2` / `STRATA_EXPERT_V2K` / `STRATA_TSUM` **四个全在** |
| 生产容器 env | 只有 `STRATA_SRC=/src` => **这四个一个都没设（全走默认关）** |
| 源码/文档覆盖 | `EXPERT_V2` 2 文件/1 文档 · `TSUM` **6 文件**/1 文档 · `V2K` 1 文件/**0 文档** · `GROUPED_V1` 2 文件/0 文档 |
| 我们的 register | `PARAM_REGISTER.tsv` 50 行里**一个都没有**（P90~P99 也没有） |

-> **这一族是我们目前发现的、最集中的一块未探索面，而且它自带「按位等价」的免责条款**（正确性先验已由上游给出；
剩下的只是「在 gfx906 上快不快」，属**纯性能问题**）。

---

## §3 第二问：ki 的 custom 引擎有用吗

### 3.1 它是什么（routeK 主源实读）

`csrc/rocm/` 清单与自我定位（头部注释逐字）：

| 文件 | 自我定位 |
|---|---|
| `moe_q_gemm_gfx906.cu`（38,578 B） | 「Fused **MoE W4A16** GEMM kernel for gfx906 (Vega 20, **no MFMA**). Port of `moe_q_gemm_rdna3.cu` for the gfx906 dense **AWQ** fast path: **fp16 activations only**（AWQ/GPTQ W4A16 on gfx906 runs fp16）; dot via **`__ockl_fdot2`（`v_dot2_f32_f16`）**, same as the proven dense `gptq_gemm` path...; `zero_offset` is a runtime argument: 0 for AWQ, 1 for GPTQ-v1 style zeros」 |
| `dense_gemv_gfx906.cu`（59,100 B） | 「**M=1 W16A16** dense GEMV for gfx906... `out[1,N] = x[1,K] @ W[N,K]^T`（all fp16, fp32 accumulation）... same structure as `LLGemm1_kernel` which saturates HBM on the big rows」 |
| `skinny_gemms.cu`（91,916 B）· `skinny_gemms_int4.cu`（31,786 B） | torch 扩展（`#include <torch/all.h>` · `ATen/cuda/CUDAContext.h`） |
| `gfx906_fa/kernel/fattn-q8.cuh`（1,260 行）· `fattn-q8-paged.cuh`（773 行） | gfx906 的手写 FA（Q8 KV） |
| `attention.cu`（142,894 B）· `moe_align_m1_gfx906.cu` · `q_gemm_rdna3*`（RDNA3，与我们无关） | 同上 |

### 3.2 能不能用在我们身上（源码级判定）

| 判据 | 事实 | 结论 |
|---|---|---|
| 宿主运行时 | 全部是 **PyTorch/vLLM 扩展**（`torch/all.h`、`ATen`、`torch_bindings.cpp`） | Strata 是独立 C++ 引擎，**没有 torch** |
| 量化契约 | 它们做的是 **AWQ/GPTQ W4A16（fp16 激活、fp16 累加 + fp32）** | Strata 的专家路径是 **GGUF IQ + q8_1 激活（int8 激活、`dp4a`）** = 不同契约 |
| 能否吃我们的权重 | routeK 的 `vllm/` 下含 `gguf` 的文件数 = **1** | **吃不了** UD-IQ4_XS 的 GGUF pack |
| 算术效率对比（芯片级，routeK 实测同卡） | routeK 的 MoE dot 用 `v_dot2_f32_f16` = **3,349 GMAC/s（0.58x fp32，延迟链探针下限；ILP>=2 时约 10 T）**；Strata 用 `v_dot4_i32_i8` = **25,877（4.44x）** | **Strata 的算术选择更优**；routeK 那条路是被他们的 AWQ/fp16 契约绑住的 |

-> **结论**：**routeK 的 custom 引擎对本项目「不可用」**，不是因为它差，而是因为
**它绑在另一个宿主（torch/vLLM）与另一个量化契约（AWQ W4A16 fp16）上**。
可用的是它的 **结论（§2 已用）、探针库、3 个 gfx906 技能、89 份 docs**（见 §4）。

---

## §4 第三问：ki 还有什么可借鉴（`docs/gfx906/` 89 份逐类挑）

按「对我们干什么用」排，**每条给路径**：

| # | 件 | 对本项目干什么用 |
|---|---|---|
| 1 | `DEAD-ENDS.md` · `DEAD-ENDS-AUDIT.md` · `REFRIGERATOR.md` | **排除台账**：连同 §2 的速率表，直接划掉一整类尝试（消 spill / 换 dot / lm_head 杠杆 / dot2 重写） |
| 2 | `ROADMAP.md` | 上游**未完成清单**（我方适用性裁决的镜子；W736 已用它避免与 #1670 重复） |
| 3 | **`dvfs-mi50.md`** | **MI50 的 DVFS/频率行为** -- 我们的读数纪律是「须声明 `Z0=off`」，这件是同一问题的成熟版 |
| 4 | **`acs.sh` · `disable_acs_p2p.sh`** | **PCIe ACS**（访问控制服务）会影响 P2P 与大包；我们关心 PCIe（`--pcie-frac` / `--pcie-mode`） |
| 5 | `running.md` | 他们的**成品服务配置**（对读我们的 `--prefill auto` / `--spec-min-p` 取值） |
| 6 | `_bench_gfx906.py` · `_bench_serve_grid_gfx906.py` · `_pp_bench.py` | **服务态 bench** -- 对标我们的 `tools/calibrate.py`；含「graph A/B 才是闸门」的落地 |
| 7 | **`prefill-multibatch-tax.md`** | 多批 prefill 的 **O(live-context) 税**；与我们的预填分辨力/份额表直接对读 |
| 8 | **`oom-256k-prefill.md`** | **约 250k token 首次 prefill OOM** -- 我们跑 **262144** 上下文，这是同一个坑 |
| 9 | `degradation.md`（137 KB）· `degradation_details.md`（182 KB） | **主机态退化**（同机可复现）；我们的 A/B 污染源，须记主机态 |
| 10 | `PROFILE-k4-step-ledger.md` · `PROFILE-gdn-bucket-breakdown.md` · `gdn_step_spy.py` · `gemm_step_census.py` | **逐 step / 逐内核账** -- 我们只有 `--stage-timing`（stage 级） |
| 11 | `DEVLOG-gdn-*.md` · `int8-investigation-qwen.md`（48,753 B） | **GDN** 与 **int8 总台账**：两家的模型都含 GDN；我们 register 有 `STRATA_PREFILL_CPU_SHARE` 一类，但 GDN 面未动 |
| 12 | `RECON-*.md`（4 份） · `cpu-stuck-threads.md` · `tp_stuck_threads_analyze_{claude,gpt}.md` · `latency-hiding.md` · `lds-layout.md` · `_worked-example-npt2.md` | 侦察记录 / 卡死诊断 / 调度与 LDS 布局 / 教科书案例 |
| 13 | `src/.agents/skills/`（3 个 gfx906 技能）+ `benchmarks/kernels/gfx906/`（40+ 探针） | 见 `W737_ROUTEK_PORT.md` §2 |

**注意 §5 的提醒**：`STRATA_HIP_WMMA` / `STRATA_SELECT_WMMA` / `STRATA_PF_GEMM` / `STRATA_HCD_EXACT` 这几个是
**WMMA 依赖**（gfx1151 的矩阵核）=> **gfx906 不可用**（我们 P96 已判）。它们**不是**我们的候选。

---

## §5 候选清单（本轮修订；插到 `W737` 的 R1 之前）

| # | 靶子 | 预期 | 成本 | 风险 | 判据 / 一票否决 |
|---|---|---|---|---|---|
| **R0a** | **`STRATA_EXPERT_V2`（S26）单变量 A/B** | 未知，但**正确性已先验**（上游用真 UD-IQ4_XS blob 做过 memcmp 位等验证） | 极低（一个 env + 一次重启） | **零**（按位等价；且我们现役就是 IQ3_S/IQ4_NL + n_embd 2560/n_ff 640，**条件完全命中**） | 服务态解码 t/s；**一票否决 = 输出 token 有任何不同**（按位等价若被打破，说明契约变了） |
| **R0b** | `STRATA_TSUM` 单变量（**只该作用于 down**：源码说对 gate/up 是 0.6-0.8x） | 低-中（harness 1.09-1.12x on down rows） | 极低 | 零（位等） | 同 R0a；**须与 R0a 串行**（同路径开关不可组合测，W723） |
| **R0c** | `STRATA_LFUSE` / `STRATA_GROUPED_V1` / `STRATA_SH_STREAM` | 未知（`SH_STREAM` 在 gfx1151 上对 **UD-IQ4_XS** 是 decode +1.8%；在其它 AMD 卡**默认关**，见 #816） | 低 | `LFUSE`/`GROUPED_V1` 需先判是否改位 | 逐个单变量；改位的须过 KL 门（**上游自己就是这么门的**） |
| R1 | 移植 ISA 反汇编规程（见 `W737` §4-P1） | 高（其它内核级结论的前置） | 低 | 无 | 能取出 Strata 构建产物的 amdgcn 并数指令构成 |
| R3 | 接受长度（MTP 的 roi） | 高 | 极低 | 无 | `draft_accepted/draft_offered` + 均长 |
| R4 | `--kv` 四档质量门 | 补尺 | 中 | 低 | **KLD 主门**（与上游 §5 的做法同源）；**禁 PPL 单独做门** |
| R5 | `--mtp-q4` | 中 | 低 | 低 | 须 R3 过 2.0 |
| R6 | `native_expert_bench` 量 K-quant vs IQ 的每-expert 成本 | 判「换权重值不值」 | 低 | 无 | 同机、同层、同 groups/tokens |
| R7 | 布局类改动押**预填**侧（见 `W737` §4-P3） | 中高 | 中高 | 中 | 预填 t/s（分辨力 1.2-1.7%），须同车记 `chunks` |
| R8 | 单卡 gfx906 读数贡献上游（补 `AMD_HIP.md:504` 的 `Not done: a single-card run`） | 外部价值 | 低 | 无 | 与 W736 的 PR/issue 同渠道 |

**顺序（修订）**：**R0a -> R0b -> R3 -> R1 -> R4 -> R0c -> R2 -> R5/R6 -> R7 -> R8**

理由：R0a/R0b **零正确性风险、条件完全命中、一次重启即得**，是当前位置上性价比最高的一步；
R3 与 R4 是「门」；R1 是其它内核级结论的前置；R0c 里有改位项，须排在 KL 门（R4）之后。

---

## §6 我不能确定的（诚实账）

1. **R0a 的收益方向未知**：`STRIX_HALO.md` §4 的「按位等价」是在**维护者的机器（gfx1151）**上验的，
   且同文档明说「**Nothing here applies to CUDA or to another AMD architecture**」
   -- 这里的 "applies" 指**那份表的性能结论**，不是指开关不存在。
   `STRATA_EXPERT_V2` 的 S26 头注释又说它用**真 UD-IQ4_XS blob** 做过 `memcmp of every output`（T 1-3）。
   -> **正确性有强先验，收益必须本机量**。我**没有**在 gfx906 上量过。
2. **`STRATA_TSUM` 的 harness 数字（1.09-1.12x / 0.6-0.8x）来自哪个 harness/哪台机**：注释只写 "harness"，未写机型；
   routeK 的教训正是「harness 快不传导到服务」。-> 必须服务态复测。
3. **`STRATA_EXPERT_V2K`（K-quant 流）我未读过它的 `s27` 实现主体**，只知道入口判据与注释；
   若真要走「换 K-quant 权重」，还须读 `s27_launch_ts` 与 `S27` 的说明段。
4. **`index.txt` 的列义我没找到权威注释**（`layer.hpp` 里搜 `index.txt` 零命中）；本报告的专家类型结论
   **来自 `native_experts.txt` 的 `gu_type/d_type` 两列**（该文件头部自带列名，可靠）与**两处恰好吻合的体积反推**。
   稠密张量的类型**未逐条核**。
5. **routeK 的 `ROADMAP.md` 我这轮没读**（只在 W736 用过它的间接结论）-> §4-2 只说它「可对读」，不含具体项。

---

## §7 落盘与出处

- 本件：`deploy/W738_KQUANT_ENGINE_PORT.md`
- **Strata 主源（容器 `strata166-407` 内实读）**：
  `src/kernels/cuda/iq_kernels.cu`（`:2005-2008` S26 段头 · `:3459-3500` v2/v2k 入口与 `amd_gu` 表 · `:3538` 「the AMD layouts cover the IQ packs' gate/up types; Unsloth's Q4_K / Q5_K take the CUDA layout below」· `:3578-3602` down 侧 `native_down_lds_kernel<20>` 与 `STRATA_D_AMD(20/23/42)` · `:3474` `STRATA_V2K(12,7)/(13,8)`）·
  `src/kernels/cuda/fused_gr.cu:1380-1381`（S26 `STRATA_TSUM` 作用于 down/up 行）·
  `src/kernels/native_expert_bench.cpp`（用法与「bit for bit」契约）·
  `include/strata/kernels/{dequant_bf16.hpp:6, native_mmvq.hpp:7, iq_kernels.hpp:1-2}` ·
  `docs/STRIX_HALO.md`（**§4 on-by-default 表 + §5 changes-bits 表 + KL 门**）· `docs/AMD_HIP.md:473-506` ·
  `/proc/1/environ`（现役 env）· `strings /src/build-906/strata`（四个开关存在性）
- **pack 侧**：`/home/albus/strata166/data/packs/huihui-ud-iq4_xs/native_experts.txt`（48 行 + 头）
- **routeK 主源**：`csrc/rocm/{moe_q_gemm_gfx906.cu, dense_gemv_gfx906.cu, skinny_gemms.cu}` 头部 ·
  `csrc/gfx906_fa/kernel/`（`wc -l`）· `docs/gfx906/`（89 份全清单）· `vllm/` 的 `gguf` 命中数
- **本项目现状**：`deploy/params/PARAM_REGISTER.tsv`（50 行，无 `EXPERT_V2` 族）·
  `deploy/params/generated/strata-huihui-ud-iq4_xs.json`（现役 16 args + 2 env）· `deploy/W737_ROUTEK_PORT.md`
