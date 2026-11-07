# W783 gfx906 自定义 FA（routeK）与我们 QSA 的源码级对照

> **[2026-10-25 04:2x 勘误，AUDIT6 P1-5] 本文的优先级已作废，机制部分仍有效。**
> P87（E0 实测）证明注意力一族（attention 2.11 + scores+topk 1.61 ms/window）合计只占 GPU 的 **6.7%**：
> 本文 §4 的 A1（Q8 量化 Q + dp4a，判据 decode >= +2%）与 A3（`v_exp_f32`）实得上限 **<= 2%**，已降级为 Q5（排在 Q1-Q4 之后）。
> 当前顺序见 `W785_MASTER_QUEUE.md`；`prompt_attn_i8v3` 在 gfx906 二进制中不存在（W783 §6.3 已自查到，当时未回改 §4）。

> 机主令：**ki 的 custom FA 重点看**；源码要真下载、真读，编译与调试一律以 166 为机。
> 本文只写有证据的结论。凡属推算都标 `[推算]`，凡属实测都给出处。
> 底稿证据：四份源码全量下载（§1）、内核资源实测（§6）、校准实测（§7）。

---

## 1 这一轮补上的一件事：源码真的落了盘

上一轮我只在 166 上 `grep` 过 Strata，routeK 只拉了 7 个 md。这一轮把四棵树全量下载并解包：

| 源码 | 大小 | 成员 | 位置 |
|---|---|---|---|
| `KIntegrated/vllm-gfx906-mobydick` @ `gfx906/main` | 40.4 MB | 7618 | `deploy/tmp/_src/rk` |
| `llama.cpp` @ pin `3cf03257` | 37.5 MB | 3983 | `deploy/tmp/_src/llm_pin` |
| `llama.cpp` @ master `36e36e63` | 38.5 MB | 4287 | `deploy/tmp/_src/llm_master` |
| `Niko1221/Strata` @ `v0.2.4.2` | 30.0 MB | 5483 | `deploy/tmp/_src/s024` |

**一致性校验**（本机副本 vs 166 上真正在编的树）：

| 文件 | 166 | 本机副本 |
|---|---|---|
| `src/kernels/cuda/qsa.cu` | `389921125bcd36d2` | `389921125bcd36d2` |
| `third_party/llama.cpp/.../mmq.cuh` | `96fa70bd5a07021e` | `96fa70bd5a07021e` |

=> 本机读的就是 166 在编的那份代码，不是"某个版本"。

**166 有什么、没有什么**（这条决定下载是否必须）：

- 有：`build022/023/024/src` 三棵 Strata 全树（各 251-254 MB），含 **vendored llama.cpp 166 MB**（tarball 里是空 submodule，所以树只在 166 上完整）
- **没有 routeK**：`/home/albus/mi50-vllm` 是 0 字节空目录，`/home/albus/vllm_patch` 只有一个 `gptq.py`
- 结论：routeK 必须下载；Strata 与 llama.cpp 以 166 为准，本机副本仅用于全文阅读与交叉核对

---

## 2 routeK 的自定义 FA 是什么

代码面 5,928 行，全部落在 `csrc/gfx906_fa/`：`fattn-q8.cuh`(1112) `gfx906_fa_gather.cu`(811) `fattn-q8-paged.cuh`(665) `gfx906_fa_launcher.cu`(611) `gfx906_fa_quant.cu`(210) `gfx906-common.cuh`(303) `ggml_shim.cuh`(243) `q8_0_quantize.cuh`(73) `gfx906-config.h`(33)。

来源标注很清楚：`gfx906-common.cuh:5` 逐字 `Vendored from https://github.com/cassettesgoboom/gfx906-fa-vllm`，是从 **llama.cpp 的 `fattn-q8.cuh` 改写**而来（`ggml_shim.cuh` 的俄语注释自述）。所以它不是我方无法企及的"新算法"，而是 **llama.cpp FA 的 gfx906 特化分支**。

### 2.1 数据布局（`gfx906_fa_launcher.cu:27-31` 逐字）

```
Q: [batch, heads_q, seq_q, head_dim]        float32
K: [batch, heads_kv, seq_kv, head_dim/32]   block_q8_0（每 32 元素 34 字节）
V: [batch, heads_kv, seq_kv, head_dim]      float16
O: [batch, seq_q, heads_q, head_dim]        float32
```

### 2.2 核心手法：**Q 也量化成 int8，KQ 走 sdot4**

这条是它和我们最大的差别。

- `fattn-q8.cuh:342-395`：`int8_t* Q_values` + `half* Q_scales`，把 fp32 的 Q 按 **32 元素一块**量化成 int8 并记 scale
- `fattn-q8.cuh:429`：`static_assert(nbatch_K % 4 == 0, "nbatch_K must be multiple of 4 for sdot4")`
- `fattn-q8.cuh:447/469`：`Q_ptr4` 一次读 16B，`sdot4` 累加后再乘 `Q_scales * K_scales`

=> KQ 的内积是 **一条 `v_dot4_i32_i8` 算 4 个 MAC**，scale 只在每 32 元素乘一次。我们的 decode attention 是 **fp32 逐元素乘加**。

### 2.3 其余六个可复用点（都带行号）

| 手法 | 位置 | 内容 |
|---|---|---|
| **K 行 padding 16** | `fattn-q8.cuh:942-943` | `K_values[nbatch_fa * (nbatch_K + K_row_padding)]`，16 字节对齐以配合 `ds_read_b128` |
| **KQ_acc 覆盖到 LDS** | `fattn-q8.cuh:608-618` | `use_kq_acc_overlay = (kq_acc_bytes <= kv_tmp_bytes)`，把寄存器数组铺到"不同时使用"的 shared 上，专门用来压 VGPR |
| **硬件 exp** | `fattn-q8.cuh:733/737` | `fast_exp_f32` = `v_exp_f32`，非 `expf` |
| **内联 causal** | `fattn-q8.cuh:661-663`、`:859-864` | 逐 lane 判绝对位置，**不物化 mask 张量** |
| **GQA 头打包 nc2** | `gfx906_fa_launcher.cu:98-147` | `nc2 in {1,2,8}`，`gqa_ratio % nc2 == 0`；**只在 decode（Sq<=2）启用**，prefill 强制回 1（`ncols=64` 的 NC2=8 会 OOB，注释逐字） |
| **KV 切分 + 合并** | `gfx906_fa_launcher.cu:139-147`、`:326-403` | `gridDim.y = kv_split`，partial 存 `(m,l)`，`fa_split_combine_kernel` 用 `max`/`exp` 归一合并 |
| **paged 直读** | `gfx906_fa_launcher.cu:435-440` | `[num_blocks, 16, Hkv, (D/32)*34]`，走 block_table，不先 gather |

### 2.4 它自己量出来的两条

1. **大 tile 必须把 occupancy 钉到 1**（`fattn-q8.cuh:65-81` 注释）：
   逐字 `occupancy pinned to 1 for the large prefill tiles so the compiler may use ~256 VGPR/lane (vs ~128 at occ=2)`，效果是 `D=128 ncols=16 was 336B, ncols=32 224B, ncols=64 48B` 的 flat-path 溢出被消掉；`D=256 ncols=16 (144B) / ncols=32 (496B)` 同理。
2. **tile 表按 ncols 分档**（`fattn-q8.cuh:26-86`）：`ncols1` 随 Sq 阶梯 64/32/16/8/4/2，且 `ncols=4` 用 128 线程而不是 256（`launcher.cu:204-210` 明确标注）。

---

## 3 为什么 FA 不能整块搬到我们身上（结构不同，不是难度问题）

| 维度 | routeK FA | 我们（`qsa_decode_attn.cu` / `layer.cpp:1250-1291`） |
|---|---|---|
| 注意力模型 | **稠密** causal FA | **块稀疏**：先 `qsa_block_scores` 打分，再 `qsa_block_topk` 选块（`layer.cpp:1256-1257`），只在选中块上算 |
| KV 布局 | vLLM paged block，`[blocks,16,Hkv,·]` | Strata 自有 pools + `qsa_kv_resolve` **从 host/SSD 流式取块**（`layer.cpp:1262`） |
| V 格式 | fp16 | `kv k8v4` = K int8 + **V int4（旋转 Q4_0）**，`qsa_decode_attn.cu:920` 明列 4 种模式 |
| Q 格式 | **int8 + per-32 scale** | **fp32**（`const float* q`） |
| head_dim | 64/128/256 | **HD=256, G=12, CHUNK=64, THREADS=256**（`qsa_decode_attn.cu:23-28`） |
| 归并 | `fa_split_combine` | `decode_attn_i8_split_kernel` + `decode_attn_merge_kernel`（已具备） |
| 预填注意力 | 同一个 kernel 扩 ncols | `qsa_prompt_attn.cu` **在 gfx906 上根本没编进二进制**（§6.3） |

结论：**FA 的 kernel 本身搬不过来**（数据布局、稀疏选择、V 量化全不同）。可搬的是 **它的四个手法**（§4）。

---

## 4 逐项可移植清单（按 ROI 排）

### A1 Q8 量化 Q + dp4a 做 KQ【最高价值】

- **机理**：K 已是 int8（我们 k8v4），只有 Q 是 fp32。把 Q 按 32 元素量化成 int8 + half scale，KQ 从"每元素 1 次 fp32 乘加 + 1 次 scale 乘"变成"每 4 元素 1 条 dp4a + 每 32 元素 1 次 scale 乘"。
- **证据**：`fattn-q8.cuh:342-395/429/447-469`；我方 `qsa_decode_attn.cu:342` 形参为 `const float* q`，`load8_q8` 把 K/V 反量化成 float 再算（`:54-59`）。
- **我方优势**：`STRATA_DP4A` 宏已在专家 matvec 里用（`native_mmvq.cu:204/552`），不是新能力。
- **代价**：Q 量化误差（约 1/127 相对），与 K 的 int8 误差同量级；需过 needle（P51 的 6/6 判据）。
- **判据**：decode 中位数 >= +2%，且 needle 6/6 不退化；否则回滚。

### A2 溢出治理：把 KQ_acc 铺到 LDS 的手法用起来

- **机理**：寄存器数组在不同时使用的 shared 区域上"覆盖"，把 VGPR 压下来。
- **证据**：`fattn-q8.cuh:608-618`；配合 occupancy 钉 1（`:65-81`，实测 336B/496B 溢出归零）。
- **我方现状（实测，§6.1）**：1646 个内核里 **101 个在溢出**，热路径上最重的两个是
  `qsa_select::block_topk_re` **1120 B/线程**（每次选择都跑，`layer.cpp:1257`）与 `fused_gr::gr_down_v3` **956 B + 256 VGPR**。
- **判据**：先由 D0 证明该变体真在跑，再改；改后 decode >= +2% 且 parity 测试全过。

### A3 硬件 exp（`v_exp_f32`）替代 `expf`

- **机理**：gfx906 有 `v_exp_f32` 一条指令；`expf` 在无 `--use_fast_math` 时走 OCML 多项式。
- **证据**：`fattn-q8.cuh:733`；我方 `qsa.cu:486` 用 `expf`，且 `CMakeLists.txt:545` 的 fast-math 条件在 gfx906 下为空。
- **反证（必须记住）**：llama.cpp 全树 `v_exp_f32` 零命中，`softmax.cu:114/128/209` 也用 `expf`。所以"routeK 用了"不等于"更快"。
- **判据**：先量 expf 在 softmax 的占比；decode >= +3% 才保留，接受 top-1 变化。

### A4 内联 causal（不物化 mask）

- 我方 QSA 是块稀疏 + `cv` 选择，本来就没有 mask 张量（`layer.cpp` 无 mask 传参）。**不需要移植**，仅作参考。

### A5 GQA 头打包 nc2（decode only）

- 我方已经是 `G=12` 头打包在一个线程里（`qsa_decode_attn.cu:24`），比 nc2=8 更彻底。**不需要移植**。
- 但它的**教训要记住**：`launcher.cu:145` 逐字 `nc2 > 1 && seq_q > 2 -> nc2 = 1`，即**打包只在 decode 开**，prefill 开会导致 OOB。我们任何"按头打包"的改动都受这条约束。

### A6 KV 切分 + 合并

- 我方已有 `decode_attn_i8_split_kernel` + `decode_attn_merge_kernel`（`qsa_decode_attn.cu:800/1026`）。**不移植**。

---

## 5 不是移植，但这一轮查出来的自身问题

### 5.1 `native_mmvq` 有一条"从未在空闲 GPU 上计过时"的保守默认

`native_mmvq.cu:1157` 逐字：

```cpp
bool g_multi_exact = true;   // until the upstream layout is timed on an idle GPU (plan rule: default only what is measured)
```

关掉它（`native_mmvq_set_multi_exact(false)`）会走 **upstream 布局**：`NW = NCOLS<=4 ? 4 : 2`、`ROWS = 2`（`:1479-1486`），注释自述"faster, equal to ncols=1 only to float rounding"。

**问题**：全树只有 parity 测试调用它（`src/kernels/mmvq_multi_parity.cpp:178`），**没有任何 env / CLI 能翻这个开关**。也就是说这个"更快但非 bitwise"的路径，我们从来没在真机上量过。

**代价**：翻掉它会同时关掉 `packed`/`il` 等专用路径（`:2072/2207/2844/3230` 都有 `ncols > 1 && !g_multi_exact` 的门），所以不是干净的 A/B，必须两向都测。

**做法**：加一个只读 env（默认不变），A/B 后按数据决定。

### 5.2 路由内核在 gfx906 上用 **fp64**

`router_top10.cu:220-226/258`：`s_ex[e] = exp((double) lv[j] - (double) mx)`、`double sum` 串行 512 次。而同文件的 `router_top10_fast_kernel` 已经用"浮点树 + 单调性区间"避开串行 fp64（`:267-281` 有完整论证）。

之所以不能用：`router_top10_wave_kernel` 在 `n_expert <= 64*8` 时**先返回**（`:456-465`），我们的 E=512 正好落进这个分支。所以 fast kernel 的优化到不了我们的路径。

**判据**：bit-identity 是与 CPU 参考对齐的手段，动之前必须确认 parity 测试覆盖；收益未知，排在后面。

### 5.3 预填注意力在 gfx906 上不存在

`grep prompt_attn_i8v3 /src/build-906/strata` = **0**，`qsa_prompt_attn.cu.o` 只有 6,256 B（无 `.hip_fatbin`）。=> 预填走的不是 prompt attention 内核，而是块稀疏那条路（同一套 `attn_chunk` + 选择）。这条纠正了我上一轮"预填 attention 有 launch_bounds(THREADS,3) 可调"的猜想：**那个内核没被编进去，调它无效**。

---

## 6 166 上的内核资源实测（不占 GPU，只读 ELF）

方法：`llvm-objcopy --dump-section .hip_fatbin` 取出 device code object，`clang-offload-bundler --unbundle --targets=hipv4-amdgcn-amd-amdhsa--gfx906` 解包，`llvm-readobj --notes` 读 amdhsa 元数据（`.vgpr_count` / `.private_segment_fixed_size` / `.group_segment_fixed_size`）。

### 6.1 全局：1646 内核，101 个溢出

| TU | 内核 | VGPR | 私有段（溢出） | LDS |
|---|---|---|---|---|
| `qsa_select` | `block_topk_re*` | 64 | **1120 B** | 0 |
| `fused_gr` | `gr_down_v3` | **256** | **956 B** | 160 |
| `iq_kernels` | `expdec_gu` | 64 | 520 B | 15,616 |
| `qsa_select` | `block_topk_re*` | 64 | 432 B | 32,908 |
| `native_flash_attn` | `attend` | **256** | **412 B** | 0 |
| `iq_kernels` | `expdec_down` | 64 | 376 B | 2,880 |
| `native_mmvq` | `native_mmvq_m*` 多例 | 64 | 36-52 B | 1.5-6 KB |
| `s2_expert_grouped` | `cpu_order_pr*` | 64 | 64 B | 0 |

参考：`fused_gr::gr_down_v3` 的另两个实例是 256 VGPR + 636 B / 312 B；`dflash2::gemm8` 多例 244-256 VGPR 但 **priv=0**（说明 256 VGPR 本身不是问题，**是"同时又要 256 VGPR 又要局部数组"才溢出**）。

### 6.2 干净的关键内核

- `router_top10_wave_kernel`：**31 VGPR / 50 SGPR / 200 B LDS / priv 0** => 路由本身没有可挖的
- `attn_chunk_kernel<...,true,...>`（decode 注意力主力）：**116-123 VGPR / priv 0** => decode 注意力没有溢出问题
- `b6_mmvq_rows`：183 VGPR / priv 0

### 6.3 由此得到的判断

1. routeK 的"occ 钉 1 消除溢出"这条，**在我方 decode 路径上没有对象**（decode 注意力 0 溢出）。
2. 真正的溢出热点在 **`qsa_select`（选择）与 `fused_gr`（GR 下投影）**，不在注意力。这与"预填期 GPU 利用率 0%、瓶颈在 CPU 专家算"的旧结论一致：注意力不是瓶颈。
3. `native_flash_attn::attend`（256 VGPR + 412 B，已是 `__launch_bounds__(128,1)`）**只在 `native_flash_attn_short` 分支用**（`layer.cpp:1277-1285`），且要求 `context <= 256`；我们没有开它。

---

## 7 校准实测（`tools/calibrate.py`，166 上跑完，rc=0，1292 s）

它自己的 42 tok/s 量级，与我们的 M 档不可直接比（prompt 不同）。

| 项 | 候选 | 中位数 | 结论 |
|---|---|---|---|
| `--spec-min-p` | 0.3 / 0.5 / **0.7** | 36.8 / 39.1 / **41.8** | **0.70 胜**，比上游默认 0.5 高 **+6%** |
| 复核 `0.36/0.5` vs `0.36/0.7` | | 38.4/38.8/36.7 vs **41.7/42.2/39.5** | 0.70 再次胜出 |
| `--pcie-frac` | 0.0 / **0.2** / 0.35 / 0.36 / 0.55 / 0.75 / 0.9 / 1.0 | 38.96 / **39.23** / 38.66 / 39.46 / 37.74 / 35.5 / 34.3 / 32.1 | **0.36 仅 +0.6%，噪声内**；0.55 起明显劣化 |
| `--pool-workers` | 20 / 13 / 10 / 5 | **41.9/38.4** / 41.0/41.0 / 40.9/37.6 / 38.2/35.4 | **20 胜**（与 P26 回滚结论一致） |
| `--adapt-*` | 默认 / 1/80/0.97 / 1/160/0.97 | **41.96/42.45** / 38.88/38.40 / 39.61/35.82 | **默认胜**，不要动 |
| `STRATA_SH_STREAM` | 0 / **1** | 40.67/37.46 / **41.63/38.35** | **1 两次都 +2.4%**（已发车，见 §8） |

三条硬结论：**`--spec-min-p 0.70` 从"历史值"升级为"本机实测最优"；`--pcie-frac` 不必改；`--pool-workers` 与 `--adapt-*` 维持默认。**

---

## 8 批次（全部以 166 为编译/调试机）

| 编号 | 内容 | 前置 | 判据 | 预计 |
|---|---|---|---|---|
| **E0** | rocprofv3 取 kernel 级占比：`block_topk`（含哪个变体）、`attn_chunk`、`native_mmvq`、`fused_gr`；同时确认 `qsa_select` 1120 B 变体是否真被调用 | 无 | 得到占比表，否则 A2/A3 不发车 | 20 min（需独占） |
| **E1** | `STRATA_SH_STREAM=1` 三档 S/M/L 复核 | 已部署 | 三档 prompt >= +1.5% 且 decode 不降 | 35 min |
| **E2** | **A1：Q8 量化 Q + dp4a**（改 `qsa_decode_attn.cu`，加 env 门控，默认关） | E0 显示注意力占比 | decode >= +2%，needle 6/6 | 改+编 30 min，测 30 min |
| **E3** | **A2：溢出治理**（`block_topk` 的 1120 B、`fused_gr::gr_down_v3` 的 956 B） | E0 显示它们是热 | decode/prefill 各 >= +2%，parity 全过 | 40 min |
| **E4** | **A3：`v_exp_f32`** 替换 softmax 的 `expf`（env 门控） | E0 量出 exp 占比 | decode >= +3% | 30 min |
| **E5** | `native_mmvq` upstream 布局（加 env，双向 A/B） | 无 | 两向都测，取优；无差异则维持 `true` | 35 min |
| **E6** | DPP 融合归约（`qsa.cu:428-436` 的 5 步 shfl 改 `v_add_f32_dpp`/`ds_swizzle`） | E0 | decode >= +2%，数值不变 | 30 min |
| **E7** | 路由 fp64 治理（需 parity 覆盖确认） | E6 后 | 无退化才留 | 30 min |
| **E8** | `--pcie-frac 0.36` 在我们自己的 M/L 档复核 | E1 | >= +1% 才改，否则维持 0.20 | 20 min |

**回滚位**：镜像 `0.2.3`（生产现用 `0.2.4`）、容器 `strata166-407.bak023`、config 备份 `*.bak_hcq8_*`；所有内核改动一律 env 门控、默认关闭，先量后开。

---

## 9 一句话

**routeK 的 FA 搬不动（稀疏 vs 稠密、V int4 vs fp16、自有 pools vs paged），但它把"Q 也压成 int8、KQ 走 sdot4"这条用到了极致——这正好是我们 decode 注意力唯一还空着的 ALU 优化点（A1）。** 至于它反复强调的"occ 钉 1 消溢出"，在我方 decode 路径上没有对象：真正溢出的 101 个内核里，热路径上的是选择器 `block_topk`（1120 B）和 `fused_gr`（956 B）。
