# W784 gfx906 源码全覆盖清点：routeK 与 llama.cpp 能移植什么

> **[2026-10-25 04:2x 勘误，AUDIT6 P1-1/P1-2] 本文 §4 的 F1 与 F2 均已撤销，执行以 `W785_MASTER_QUEUE.md` 为准。**
> 1. **F1（溢出治理）撤销**：`gr_up75_kernel` 在 HIP 下不执行（`fused_gr.cu:1193-1196` `up75_on()` 直接 return false），
>    且 HC_Q8=1 时实际运行的 `gr_down_multi_kernel<2560,8,true>`（114 VGPR）与 `gr_up_multi_kernel<6,true,true>`（107 VGPR）
>    **私有段都是 0**——没有溢出可治。§3 的 F2 表格里那些 956 B / 88 B 属于非默认路径。
> 2. **F2（`--kv-grow` 换 +1487 槽）不可达**：三臂实测 `expert_slots` 恒为 9901；`src/core/vmm.cpp:158/167` 把 HIP VMM
>    限定在 `!defined(STRATA_HIP_GFX906)`，`:299-303` 返回 false，同处注释逐字点名 gfx906。
> 3. 本文"§1-§3 的机理与关闭清单"仍然有效；**§4/§5 的排期作废**。

> 机主令：两项源码都深入研究，**一项项深挖机理**，覆盖要全，形成方案并入总方案单独章节，并在总方案里统一排期。
> 本轮与 W783 的差别：W783 只读了 FA 一族；本轮把 **routeK 202 个 gfx906 相关文件、45 个自有开关、13 份 DEVLOG（9,900 行）、llama.cpp 两棵树 68 个差异文件**全部过了一遍，并且**拿到了 E0 的分阶段实测**，因此每一项都能给出"机理 + 我方现状 + 价值上限"三件事，而不是只说"能不能搬"。

---

## 1 覆盖范围与证据

| 面 | 数量 | 来源 |
|---|---|---|
| routeK 提到 gfx906/vega20 的源码文件 | **202** | `grep -rl -iE "gfx906\|vega ?20"`（10 目录：`csrc/*` 15、`vllm/*` 39、`benchmarks/*` 28、`tests` 5） |
| routeK 自有开关 | **45** | `VLLM_GFX906_*` 14 类 + `GFX906_FA_*` / `GFX906_*` 31 类 |
| routeK 裁决记录 | 11 条 DEAD-END、5 条 SHIPPED、3 条 OPEN | `docs/gfx906/DEAD-ENDS.md`（逐行：假设、门、裁决、回退、注释） |
| routeK 文档 | 9,900 行 / 45 文件 | `docs/gfx906/*.md` |
| llama.cpp | pin `3cf03257` vs master `36e36e63` | `ggml-cuda` 68 个文件差异 |

源码位置：`deploy/tmp/_src/{rk,llm_pin,llm_master,s024}`。Strata 与 llama.cpp 的副本与 166 逐字节一致（`qsa.cu` `389921125bcd36d2`、`mmq.cuh` `96fa70bd5a07021e`）。

---

## 2 E0 实测：先量上限，再谈移植

> **[2026-10-25 06:2x 补勘误，`AUDIT7` 发现 `AUDIT6 P2-8` 承诺的这条整改从未执行] 本节有三处要改：**
> 1. **`74.76 ms/window` 是墙钟，不是 GPU stages 的总和。** 本节同一段里又写 `GPU stages total 55.65 ms/window`，
>    而下面的阶段占比是按 **55.65** 算的。两个数不能混着用（`74.76` 与 `55.65` 差 19.11 ms，是主机侧开销）。
> 2. **本节所属的 `P87` 已作废**（`P91` 取代），但作废理由不是"表不自洽"——见 `AUDIT6 P2-7` 的撤回banner。
> 3. **"预填期 GPU 0%"这个前提是错的**（`AUDIT6 P2-8`）：`rocm-smi` 每 1 s 直读 49 样本为 `100 x42 / 99 x4 / 98 x1 / 68 x1 / 0 x1`，
>    中位 100、零值 2%。本节据此提出的"把专家算力搬到 GPU"方向不成立。
> => 本节的**数字**可作历史对照，**结论**一律以 `P91` / `W786 §2.1` 为准。

`STRATA_DECODE_TIMING=1` + `STRATA_VERIFY_PROFILE=1`（引擎自带，`generate.cpp:15208` 那段），M 档 21,827 token 提示、97 窗口稳态：

```
strata decode timing: 96 windows, avg T 3.47, 3.33 tokens/window, 74.76 ms/window
  = verify 56.36 (GPU-reach wait 34.64 + per-layer host 18.83 [CPU 17.75] + stage 0.04)
    + commit/emit 0.05 + draft 7.04
GPU stages total 55.65 ms/window  =>  verify 期间 GPU 占用 98.7%
```

**GPU 每窗口 55.65 ms 的去向（毫秒，括号为占比）**

| 阶段 | ms | 占比 | 说明 |
|---|---|---|---|
| **VRAM hits** | 7.44 | **13.4%** | 专家从显存缓存取（GDN 5.63 + QSA 1.81） |
| **HC down/up** | 7.15 | **12.8%** | hyper-connection 四个投影（GDN 5.36 + QSA 1.79） |
| **waitB** | 6.49 | **11.7%** | 等专家数据就位 |
| **量化+dense GEMV** | 6.25 | **11.2%** | `q8+qkv/q-idx` 3.92 + `q+q-idx` 2.18 + `q8+kv-idx` 0.15 |
| **waitCPU** | 4.01 | **7.2%** | 等 CPU 侧专家算完 |
| router+plan+bell | 3.87 | 7.0% | 路由与规划 |
| attention | **2.11** | **3.8%** | QSA 注意力本体 |
| scores+topk | **1.61** | **2.9%** | 块选择（含 1120 B 溢出那个内核） |
| head / z / out-proj / shared+quant / rec / ab / conv / PCIe / copy | 13.7 | 24.6% | 其余 |
| KV append + k/v rope + kv-resolve + gate | 0.77 | 1.4% | |

三条硬结论：

1. **注意力一族（attention + scores+topk）合计 3.72 ms = 6.7%**。就算把注意力做到零，也只能省 6.7%；把 Q8 量化、DPP 归约、`v_exp_f32` 全做上，按每项 20-30% 计算，**合计上限约 1.5-2%**。
2. **专家流（VRAM hits + waitB + waitCPU）合计 17.94 ms = 32.2%**，是最大的一块。
3. **HC 投影 7.15 ms = 12.8%**，且它是唯一验证过有收益的方向（`STRATA_HC_Q8=1` 已采纳，+0.6%）。

=> 本轮据此**重排优先级**，并**下调 W783 里 A1/A3/E6 的位置**（它们不是错，是上限太低）。

---

## 3 家族逐项清点（机理、证据、上限、裁决）

### F1 自定义 FA 后端（routeK 最强项，但结构不同）

| 项 | 机理（原文/行号） | 实测（它自己） | 我方现状 | 裁决 |
|---|---|---|---|---|
| Q8 KV + **Q 也量化** + `sdot4` | `fattn-q8.cuh:342-395` Q_values/Q_scales per-32；`:429` sdot4 | 注意力 194 到 **72 µs/layer（2.7x）** | K 已 int8；**Q 是 fp32**，K/V 反量化成 float | 上限 3.8%，**降级为候选**（原 A1） |
| GQA 头打包 `nc2` | `launcher.cu:98-147`，仅 decode（`:145` `seq_q > 2 -> nc2=1`） | Sk=2048：NC2=1/2 + KVSPLIT=16，102.8 到 **76.1 µs** | 已按 `G=12` 把 12 个头压进一个线程 | **不移植**（我们更彻底） |
| KV 切分 + 合并 | `:326-403` `fa_split_combine`（m,l 归一） | 同上 | 已有 `decode_attn_i8_split_kernel` + merge | **不移植** |
| 直读 paged（不 gather） | `:435-440` block_table | gather 路径 **43.6 µs/layer** 税，净得 122 µs | 我们本就无 gather（pools + resolve） | **不移植** |
| 融合 gather+量化（bit-exact） | `gfx906_fa_gather.cu`（`q8_0_quantize.cuh:14` 逐字 "bit-equal"） | 省一次单独量化 | 无对应阶段 | 不适用 |
| V2 融合 gather（416 WG） | — | serving 里 **退化 7 倍**（285 vs 42 µs） | — | **反面证据，记住** |
| 持久化内核 `GFX906_FA_PERSIST` | 减少重复启动 | SHIPPED | 我们按层启动，但 attention 只 3.8% | 不采用 |
| 内联 causal（不物化 mask） | `:661/859` | 省一张 `[B,Sq,Sk]` fp16 表 | 我们块稀疏，本就无 mask | 不适用 |
| K 行 padding 16 配 `ds_read_b128` | `:942` | — | 我们有其它对齐手法 | 不适用 |

### F2 溢出治理（**唯一有真实对象的一条**）

| 项 | 机理 | 证据 | 我方现状 | 裁决 |
|---|---|---|---|---|
| 大 tile 把 occupancy 钉 1，放开到 ~256 VGPR | `fattn-q8.cuh:65-81` 逐字 "occupancy pinned to 1 ... ~256 VGPR/lane (vs ~128 at occ=2)" | flat 路径溢出 **336 B / 224 B / 496 B 归零** | `fused_gr::gr_down_v3` = **256 VGPR + 956 B 溢出**，正是 HC down（6.4% 的时间） | **采纳为 F2 主项** |
| 把寄存器数组铺到"不同时使用"的 LDS | `:608-618` `use_kq_acc_overlay` | 降 VGPR | `fused_gr::gr_up75` 另有 72-88 B 溢出 | 同上一起做 |

注：`qsa_select::block_topk` 的 1120 B 溢出虽然更大，但它所在的 `scores+topk` 只占 2.9%，上限低，排 F2 之后。

### F3 MoE 解码 GEMM 重排（它全部试完并关闭）

| 项 | 结论（它自己） |
|---|---|
| gemm1 V1 全 K 单波直写 | **REJECTED 2.2x 慢**（64 block 撑不住 128 KB 流） |
| gemm1 NPT=2（z 切分最优点） | **DEAD-END**：census 说 -186 µs/step，墙钟中性，"第 3 次连续 transfer 失败" |
| gemm1 V3 fp32 scratch K 切分 | DEAD-END（多出 ~184 µs/step） |
| gemm1 V4 减 CAS fan-in（NPT=8/z=32） | DEAD-END（单调变差 27.8 到 33.4） |
| gemm2 V2 M=1 重排（lane 列） | NEUTRAL（standalone 1.18x，模型内不转移） |
| K-split GEMV（kc=512） | **REJECTED 2.4-4.2x 慢**；"M=1 是 latency/launch-bound，不是 occupancy-bound" |

裁决：这是一整套**否定证据**，直接覆盖我方两个待办（P77 pool-tasks 已否决、K 切分想法）——**不必再试**。

### F4 MoE 预填 GEMM

| 项 | 机理 | 实测 | 我方 | 裁决 |
|---|---|---|---|---|
| BM 按专家行数分档 | `moe_q_gemm_gfx906.cu:604-611` + DEVLOG 逐字 `em > 512 -> BM=8, NPT=2` | M=512：3027 到 **2917 µs（+3.7%）** | 我方预填 **GPU 利用率 0%**（瓶颈在 CPU 专家） | **不采纳**（前提不成立） |
| 双缓冲权重预取 | — | **DEAD-END：256 VGPR + 重溢出，5.8x 慢** | 我们若给 `s2_expert_grouped` 加双缓冲也会踩同一坑 | **反面证据，禁止** |
| b128 LDS 读 | — | SHIPPED 但**中性**（3027 到 3049） | 已有 `uint4/float4` 362 处 | 不适用 |
| zero-fill 融合（省一次启动） | — | **DESCOPED：设计有竞态** | — | 不采纳 |
| cudagraph 上限 | 配置 | SHIPPED 2.2x（vLLM 专属） | 我们用持久化 CUDA graph 已有 | 不适用 |

### F5 dense GEMV（我们 GPU 上最大的一块，11.2%）

| 项 | 机理 | 实测 | 我方 | 裁决 |
|---|---|---|---|---|
| RPT/KCHUNK 按形状分档 | `dense_gemv_gfx906.cu:787-802`：`kchunk=2048 && (N==256 或 N>=2048) -> RPT=2`，其余 RPT=4；`kchunk=1024 -> RPT=(N%2?1:2)` | 逐形状 0.95-1.29x HBM 地板 | 我方 `s_gemv` / `native_bf16` 有自己的 NW/ROWS | **方法可借：按形状扫，不照搬数值** |
| M=5..16 用 exact-M 模板（RPT=1） | `:727-750` | speculative 形状 | 我们 spec=6，正好落在 M=5..8 | **候选**（需先看我们是否已按 M 分档） |
| W16A16 长 K（K=17408） | 行并行 + `__ockl_fdot2` | SHIPPED，227.6 vs 795 µs（101% 地板） | 我方是 Q8_0/IQ4_XS，非 fp16 | 不适用 |
| lm_head GEMV 杠杆 | — | NEUTRAL（3114 vs 3128 µs，已在地板） | — | **"lm_head 还能挖"这个念头作废** |

### F6 topk / router

| 项 | 机理 | 实测 | 我方 | 裁决 |
|---|---|---|---|---|
| M=1 专用单波 topk | `moe_topk_gfx906.cu:1-40`：一颗 64 lane 波，去掉 (64,4) block 的行机器 | 17.9 到 **12.5 µs/call**；但模型内 **NEUTRAL** | 已有 `router_top10_wave_kernel`（31 VGPR、priv 0） | **不移植**（已具备） |
| LDS+barrier 版 topk | — | **35.5 µs，比 shuffle 差** | — | 反面证据 |
| width-64 版（补 32 个 -inf lane） | — | 更慢（2x 每 lane 工作量） | — | 反面证据 |
| 路由 fp64 治理 | 我方 `router_top10.cu:220-226` 用 `exp(double)` + 512 次串行 double 加 | 我方 `router+plan+bell` = 3.87 ms（7.0%） | 有 `router_top10_fast_kernel` 但被 wave kernel 先返回挡掉 | **候选（F4）**，需 parity 覆盖 |

### F7 指令级：dp4a / dot2 / DPP / exp

| 项 | llama.cpp 原文 | 我方实测 | 裁决 |
|---|---|---|---|
| gfx906 原生 dp4a | `common.cuh:722` `#if defined(CDNA) \|\| defined(RDNA2) \|\| defined(__gfx906__)` 走 `__builtin_amdgcn_sdot4` | Strata 的 `hip_compat/intrinsics.hpp:18-53` **没有 gfx906 分支**，落到 `#else` 逐字节模拟；但**反汇编 `native_mmvq` 有 27,384 条 `v_dot4`、`iq_kernels` 43,110 条** | **已是硬件指令，无需改**（编译器把模拟模式 pattern-match 成 sdot4）；这条纠正了我一开始的怀疑 |
| `v_dot2_f32_f16` | `common.cuh:769` 也给 `__gfx906__` 开 | 我方全树 `v_dot2` = **0 条**；但我们权重是 int8/IQ4_XS，非 fp16 | 不适用（除非有 fp16 路径，见 F9） |
| DPP 融合归约 | 见 routeK `gfx906-common.cuh:80-149`（`v_add_f32_dpp` + `ds_swizzle`） | 我方 `qsa.cu:428-436` 是 5 步 `__shfl_xor_sync` | 上限在 attention（3.8%）内，**降到 F5 之后** |
| `v_exp_f32` | `gfx906-common.cuh:31-40` | 我方 `qsa.cu:486` 用 `expf`，构建无 `--use_fast_math` | 同上，**降级** |

### F8 llama.cpp：pin 与 master 对 gfx906 **一字不差**

```
diff <(grep -n gfx906 pin/*) <(grep -n gfx906 master/*)
  只有行号变化（722/769 -> 714/761），内容完全相同
```

- `mmq.cuh` 的 `get_config_gcn` 差异仅在 NVFP4 前置（master 新增 `prec_src1` 门），**GCN tile 表未变**
- master 的 `ggml_cuda_mmq_get_config` 多一个 `prec_src1` 参数，这正是我方 4 参调用编不过的原因（已记）
- 结论：**llama.cpp 最新版对 gfx906 没有任何新增优化**。上一轮"不跟 master"的决定由此得到正面支持，而不只是"编不过"

### F9 CPU 侧（我们预填的真瓶颈）

| 项 | 结论 |
|---|---|
| routeK CPU MoE | `csrc/moe/dynamic_4bit_int_moe_cpu.cpp` 只有 172 行，第 5 行逐字 "`_dyn_quant_matmul_4bit` is only available on AArch64" => **x86 上是个桩，无可移植** |
| llama.cpp CPU IQ4_XS | 我方 `iq_avx2_rows.inl` 是它的改写；0.2.4 上游新增的 `EX` 模板只服务 DeepSeek 路径（`:EX=false` 时主引擎行序不变），已在 W780 核实 |
| 我方 CPU 现状 | 20 worker / AVX2（无 AVX-512）；`waitCPU` 4.01 ms（7.2%）是 CPU 专家算完的等待 |

---

## 4 净结果：四项存活，其余关闭

| 新编号 | 项目 | 机理来源 | 价值上限（E0） | 判据 | 成本 |
|---|---|---|---|---|---|
| **F1** | `fused_gr::gr_down_v3` 溢出治理（occ 钉 1 / LDS 覆盖） | routeK FA `:65-81` + `:608-618` | HC down 6.4%（+ up 共 12.8%） | decode >= +2% 且 parity 全过 | 改+编 40 min |
| **F2** | `kv-grow` 释放 K/V 3.35 GiB 换 **+1487 专家槽（+15%）** | 我方 `generate.cpp:5154` 门 + 源码注释 3.35 GiB | 专家流 32%（VRAM hits + waitB） | decode >= +2%，无换出 | 60 min（要拆 resident-experts） |
| **F3** | 路由 fp64 治理（切 `router_top10_fast_kernel` 或改造 wave kernel） | 我方 `router_top10.cu:220-226` | router 7.0% | decode >= +1%，parity 位等 | 40 min |
| **F4** | dense Q8 GEMV 按形状扫 (NW/ROWS/BPI) | routeK `dense_gemv:787-802` 的方法 | 11.2% | 逐形状 >= +3% 才改 | 45 min |
| — | A1 Q8 量化 Q + dp4a | routeK FA 核心 | attention 3.8%，实得 <= 1% | **降级：只有在 F1-F4 都做完后再看** | — |
| — | DPP 归约 / `v_exp_f32` | routeK common | 同上 | **降级** | — |
| — | `native_mmvq` upstream 布局（原 E5） | 我方 `:1157` 从无计时 | 未知，先测 | 保留为 F5（便宜，可随时插） | 35 min |
| — | `block_topk` 1120 B 溢出 | 我方 ELF 实测 | scores+topk 2.9%，实得 <= 0.5% | 降级 | — |

**明确关闭（附理由）**：FA kernel 本体、GQA 打包、KV 切分合并、gather 融合、paged 直读、persist、MoE BM 分档、双缓冲、b128 LDS、zero-fill 融合、topk 单波、LDS topk、width-64、K-split GEMV、dense W4A16 自制 GEMV、lm_head 杠杆、llama.cpp 跟版、routeK CPU MoE、dot2。

---

## 5 统一排期（并入总方案 §11）

| 序 | 编号 | 内容 | 依赖 | 预计 | 停生产 |
|---|---|---|---|---|---|
| 1 | F5 | `native_mmvq` upstream 布局（加 env，双向 A/B） | 无 | 35 min | 45 s x2 |
| 2 | F1 | `gr_down_v3` 溢出治理 | 无 | 40 min + 测 20 | 45 s |
| 3 | F3 | 路由 fp64 | parity 覆盖确认 | 40 min + 测 20 | 45 s |
| 4 | F4 | dense Q8 GEMV 形状扫 | 无 | 45 min | 45 s |
| 5 | F2 | `kv-grow`（拆 resident-experts，+1487 槽） | F1-F4 完成（避免混因） | 60 min + 测 30 | 5 min |
| 6 | F6 | A1/DPP/exp（若前五项收益已到位则不做） | F1-F5 | - | - |

纪律（本轮再次验证）：
1. **先量上限再动手**。E0 一小时内否掉了三个"看起来最像优化"的方向。
2. **standalone 微基准赢不等于 serving 赢**（routeK 连续三次栽在这上面，我方 `--pool-tasks` 同构）。
3. 任何源码改动 **env 门控、默认关**，编译与调试只在 166。

---

## 6 一句话

routeK 的 gfx906 优化**能搬的只有两条方法论**——"大 tile 用 occupancy 换 VGPR、把寄存器数组铺到 LDS"（正好对上我方 HC 投影 956 B 溢出，12.8% 的时间）和"按形状分档 GEMV"（对上我方 11.2% 的量化+密 GEMV）；**它的 FA 不能搬**（稀疏 vs 稠密、V int4 vs fp16），**llama.cpp 对 gfx906 没有任何新增**（pin 与 master 一字不差），**它的 CPU 路径在 x86 上是个桩**。而按 E0 实测，我方最大的一块是**专家流 32%**，那块 routeK 没有任何答案——只能靠 `kv-grow` 多装 1487 个专家槽来解决。
