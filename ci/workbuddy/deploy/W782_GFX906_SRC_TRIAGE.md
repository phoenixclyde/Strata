# W782 gfx906 专属优化：三方源码级对照（routeK / llama.cpp / Strata）

> 2026-10-25 02:0x-03:0x · 机主令：「ki 的项目中的源代码和 llama.cpp 的源代码，请深入研究，看有没有针对我们的架构 gfx906 的专门优化可以移植过来的。必须一项项深挖机理，必要时上网查。并将明确后的方案并入调优方案中，成立单独章节，并在总方案中统一安排计划。」
> 方法：**三方对照**（routeK 的 gfx906 kernel / llama.cpp pin 3cf03257 / Strata 0.1.49.2），每条给文件+行号，再判"能不能移、移了会不会变数值"。
> 这份是 W776 总方案新增章节（§12）的详细底稿。

---

## 0 结论：只有两条真能移，一条无风险、一条有精度代价

| 编号 | 机理 | 可移？ | 数值影响 | 预期 |
|---|---|---|---|---|
| **M1** | warp 归约用 **`v_add_f32_dpp` / `v_max_f32_dpp` 融合**（shuffle 与加法合成一条） | **能，且干净** | **none（加法顺序相同）** | 归约指令数约减半 |
| **M2** | `v_exp_f32` / `v_rcp_f32` 硬件指令替代 `expf` / 除法 | 能，但有代价 | **有（exp 精度 2^-10）** | softmax 的 exp 从 ~12 条降到 1 条 |
| M3 | `readfirstlane`（SGPR 广播波内一致值） | 能 | none | 小 |
| M4 | LDS `ld+1` padding | **不用移**：Strata 已有 | — | — |
| M5 | `b128` LDS / `dwordx4` 全局加载 | **不用移**：Strata 已有 | — | — |
| M6 | MMQ 的 GCN tile 配置 | **不可移**：同一个 pin，本来就是同一份 | — | — |
| M7 | MoE GEMM 的 BM 分档 | **不可比**：Strata 不是模板 block-M 结构 | — | — |
| **M8** | **（反向发现）Strata 自己的 double 运算**：sigmoid 与 RMSNorm 用 fp64 | 不是移植，是自伤 | **有（fp64->fp32）** | 可能最大 |

---

## 1 M1：warp 归约的 DPP 融合 —— 本报告唯一"干净可移"的项

### 1.1 机理

gfx906 的 DPP（Data Parallel Primitives）允许**一条指令同时完成 lane 置换和 ALU 运算**：

```
v_add_f32_dpp v0, v0, v0 quad_perm:[1,0,3,2] row_mask:0xf bank_mask:0xf
```

一条指令 = 「把 lane i^1 的值取来 + 加到 v0」。而常规写法：

```cpp
v += __shfl_xor_sync(mask, v, 1);   // 编成 v_mov_b32_dpp（或 ds_bpermute）+ v_add_f32 = 2 条
```

**归约 5 步：常规 10 条，DPP 融合 5 条。** 而且 DPP 走的是 wave 内的数据通路，**不占 LDS、不需要 `s_waitcnt lgkmcnt`**。

### 1.2 三方证据

| 方 | 实现 | 位置 |
|---|---|---|
| **routeK** | `DEFINE_FUSED_DPP_F32(hip_add_xor1_f32, "s_nop 4\n", "quad_perm:[1,0,3,2]", "v_add_f32_dpp")`，另有 xor2（`quad_perm:[2,3,0,1]`）、xor8（`row_ror:8`）；xor4 用两条 DPP 拼；xor16 用 `ds_swizzle_b32 offset:swizzle(SWAP,16)` | `csrc/gfx906_fa/kernel/gfx906-common.cuh`（第 79-130 行附近） |
| **llama.cpp** | 未使用 DPP 融合，走通用 `__shfl_xor_sync`；全树 grep `v_add_f32_dpp` / `__builtin_amdgcn_exp` **零命中** | `ggml/src/ggml-cuda/` |
| **Strata** | `qsa.cu:428-436`：`for (int o = 16; o > 0; o >>= 1) v = fmaxf(v, __shfl_xor_sync(0xffffffffu, v, o));`（`warp_sum` 同形） | `src/kernels/cuda/qsa.cu` |

### 1.3 为什么判"干净"

`v_add_f32_dpp` 只是把"取 lane 邻居"和"加法"合成一条指令，**加法的操作数与顺序完全不变** => IEEE 结果逐位相同。
routeK 里的 `s_nop 4 / s_nop 1` 是给 DPP 的依赖间隔用的，不动数值。

### 1.4 一个必须核实、不能凭源码断言的点

`qsa.cu:428` 的循环 `o = 16,8,4,2,1` **只覆盖 32 个 lane**，而 gfx906 的 wave 宽是 **64**。
两种可能：
- (a) 该 kernel 的线程模型按 32 分组（`WARPS = THREADS/32`，`qsa.cu:62 THREADS=128 => 4`），归约只在自己的 32 lane 组内 —— 那是对的；
- (b) 若它假设整 wave 参与，则高 32 lane 未参与 —— 那是缺陷。

**不能只看源码下定论**，要用 ISA/profiler 核：`llvm-objdump` 该 kernel 的 `v_add_f32_dpp`/`v_mov_b32_dpp` 数量与 `s_waitcnt` 形态。**这条放在 M1 发车之前当门禁。**

---

## 2 M2：`v_exp_f32` 硬件指数 —— 能移，但要接受精度代价

### 2.1 机理

gfx906 有硬件指数/对数指令（`v_exp_f32`、`v_log_f32`、`v_rcp_f32`），**单指令**；而标准 `expf()` 在没有 `--use_fast_math` 时走 `__ocml_exp_f32`，是 10-15 条指令的多项式。

### 2.2 三方证据

| 方 | decode softmax 的 exp | 位置 |
|---|---|---|
| **routeK** | `fast_exp_f32`：`asm("v_exp_f32 %0, %1" : ... : "v"(x * LOG2_E))` | `gfx906-common.cuh` |
| **llama.cpp** | **`expf`**（`softmax.cu:114/128/209`），全树无 `v_exp_f32` | `ggml/src/ggml-cuda/softmax.cu` |
| **Strata** | **`expf`**：`qsa.cu:486 const float e = expf(w[j] - mx);`；预填 attention 则用 `exp2f` + `scale_log2` 吸收（13 处） | `src/kernels/cuda/qsa.cu` / `qsa_prompt_attn.cu` |

**关键**：gfx906 构建**不加 `--use_fast_math`**（`CMakeLists.txt:545` 的条件是 `$<IF:$<BOOL:${STRATA_HIP_GFX906}>,,--use_fast_math>` —— gfx906 为真时展开为空）。所以 `expf` 走的是精确路径。

### 2.3 为什么判"有代价"

`v_exp_f32` 的相对误差约 2^-10（1e-3 量级），softmax 之后要归一化、再压 fp16，**通常可接受，但会改变答案**（我们已经有 `STRATA_HC_Q8` 这样"改答案"的先例，需同样对待：单变量车 + 同臂重复对照）。

**而且注意一个反常事实**：llama.cpp 全树都不用 `v_exp_f32`。要么它没试过，要么试过不划算（例如 softmax 不是瓶颈、或精度门不过）。**这条在发车前必须先量"expf 占 decode 的多少"**，否则可能白改。

---

## 3 M3：`readfirstlane`（SGPR 广播）—— 能移，收益小

`__builtin_amdgcn_readfirstlane(x)` 把 wave 内一致的值从 VGPR 搬到 SGPR，减少每 lane 重复计算与寄存器压力。routeK 用它包了 `float/int/half` 三种（`sgpr_broadcast_*`），典型用于 `scale`、`1/sqrt(d)`、行基址这类波内常量。

Strata 检索：`__builtin_amdgcn_*` 只出现在 `iq_kernels.cu`（`__builtin_amdgcn_perm` 做 IQ 反量化的字节置换）和 `fused_gr.cu`（`s_memrealtime`/`s_sleep`），**没有 `readfirstlane`**。

收益量级：小（省几个 VGPR、少几次重复乘）。**排在 M1/M2 之后。**

---

## 4 M4-M7：查完不用移的四项

| 项 | 判定 | 证据 |
|---|---|---|
| M4 LDS `ld+1` padding | **Strata 已有** | `dflash2.cu:107 __shared__ float Sc[32 * 33]`（32×33）、`:239 pbase[tid * 130]`；`qsa_decode_attn.cu:355` 用转置布局 `spt[CHUNK][G]` + float4（等价解法） |
| M5 `b128` LDS / `dwordx4` | **Strata 已有** | 全目录 `__shared__` 324 处、`uint4/float4` 362 处 |
| M6 MMQ 的 GCN tile 配置 | **同一份** | 我们与 routeK 都用 llama.cpp pin 的 `mmq.cuh:263 #ifdef GCN -> get_config_gcn`；pin 未变（3cf03257） |
| M7 MoE GEMM 的 BM 分档 | **结构不可比** | routeK 是 Triton/AWQ 的 `BM`；Strata 的专家 GEMM 在 `s2_expert_grouped.cu`（`moe_hit_grouped_s2`），无 `BM` 维度；`native_moe.cu` 229 行是 combine kernel |

---

## 5 M8（反向发现）：Strata 自己在用 fp64，而输出是 fp16

这不是"移植"，是**我们自己的浪费**，但量级可能比 M1/M2 都大。

### 5.1 证据

```cpp
// qsa.cu:513-521  qsa_gate_apply_kernel
const double g = (double) q_full[((size_t) h * 2 * head_dim) + head_dim + d];
const double sig = 1.0 / (1.0 + exp(-g));          // <-- fp64 的 exp()
out[i] = f16_from_f32((float) ((double) attn[i] * sig));   // <-- 结果压成 fp16
```

- 用 **double 的 `exp()`**，最后却 `f16_from_f32` 压成 **fp16**（约 3 位十进制）。精度全浪费。
- `qsa.cu:173-217` 另有 `__ddiv_rn` / `__dsqrt_rn` / `__dadd_rn` 的 fp64 RMSNorm 路径。

### 5.2 调用面（不小）

| 调用点 | 说明 |
|---|---|
| `src/core/layer.cpp:1298` | 每层 |
| `src/core/verify.cpp:1902` | 每个 verify 窗口，按 `tb * NH * HD` 分块 |
| `src/core/mtp.cpp:1037` | MTP 草稿层，`T * NH` |

=> **decode 的每个 verify 窗口、每一层、每个 MTP 草稿都要过一次 fp64 exp**。MI50 的 fp64 吞吐是 fp32 的 1/2，但 `exp(double)` 是**软件库**（几十条指令），不是硬件指令。

### 5.3 但必须谨慎

fp64 在这里**可能是故意的**：`1/(1+exp(-g))` 的 sigmoid 在 g 很大时有溢出/下溢，双精度能稳；而且 QSA 的 gate 可能对数值敏感。

**所以 M8 的发车顺序**：先用 `STRATA_ROUTE_STATS` 或 rocprof 量 `qsa_gate_apply_kernel` 的耗时占比 -> 若 >2% 再改 -> 改后必须过同臂重复对照（我们已知答案非确定，只能看"无反向证据"+ 分布）。

---

## 6 并入总方案的执行计划

> 已同步写入 `W776_TUNING_MASTER_PLAN.md` 的新 §12 与 §4 计划表。

| 批 | 内容 | 前置门 | 单变量 | 判据 |
|---|---|---|---|---|
| **D0** | 用 rocprof/ISA 量三件事：① `qsa_gate_apply` 占 decode 的比例 ② `warp_max/warp_sum` 的实际 DPP 形态与 lane 覆盖 ③ `expf` 在 softmax kernel 里的指令数 | 无（只读） | — | 拿到三项占比/形态数据，否则后面全不发 |
| **D1** | M1：`warp_max/warp_sum` 换 DPP 融合 | D0 显示归约占比 >1% 且 lane 覆盖正确 | 是 | decode 中位数 >=+2%；答案同臂无系统性差异 |
| **D2** | M8：`qsa_gate_apply` 的 fp64 -> fp32 | D0 显示该 kernel >2% | 是 | decode >=+3%；fp16 输出与旧值在 ulp 级 |
| **D3** | M2：softmax 的 `expf` -> `v_exp_f32` | D0 显示 softmax >3% | 是 | decode >=+3%，且接受 top-1 变化（与 HC_Q8 同级风险） |
| **D4** | M3：readfirstlane | 前面都做完 | 是 | 收益 <1% 就放弃 |

**这几批都要改 C++ 源码 -> 重编镜像**，不是改配置。所以必须排在"配置类调优"之后（calibrate 正在跑的那批）。

---

## 7 一句话

**三方对照下来，真正"gfx906 专属且我们没用"的只有一件半：DPP 融合归约（干净、无精度风险）和硬件 exp（有精度代价、连 llama.cpp 都不敢用）；而查的过程中发现我们自己有一处更大的浪费——sigmoid 用 fp64 算完压成 fp16。**
