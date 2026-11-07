# 编译开关与运行时 switch 全量对账：0.1.42 镜像 vs 上游 0.1.47 官方配方

> 目的：回答「结合 0.1.42 生产容器的编译参数/switch，有哪些可以替代上游最佳实践中的参数」。
> 方法：两代镜像的 `CMakeCache.txt` 实读 diff + 0.1.47 源码（`deploy/tmp/src022`）逐项门控核实 + 历史实测件交叉。
> 结论：**编译开关层无可补项；三个"像解药"的开关全部源码级否决；两个运行时候选已被实测/上游量化否决。**

## 1 两代镜像 CMakeCache 全量 diff（实读）

| 项 | 0.1.42 镜像 | 0.1.47 镜像（`strata-gfx906:0.2.2`） | 判定 |
|---|---|---|---|
| `STRATA_MMQ_KQUANTS` | ON | ON | 同（我按官方配方未传，默认即 ON） |
| `STRATA_NATIVE_EXPERTS` | ON | ON | 同 |
| `STRATA_ENABLE_CUDA` | ON | ON | 同（`HIP_GFX906` 自动打开） |
| `STRATA_ENABLE_HIP` | OFF | OFF | 同 |
| `STRATA_HIP_GFX906` | ON | ON | 同 |
| `STRATA_PREFILL_MMQ` | OFF | OFF | 同 |
| **`STRATA_Q6K_EXPERTS`** | **OFF** | **ON** | **上游 0.1.47 改了默认** |
| `STRATA_MMQ_TQ_OVERLAY` | —（无此项） | ON | 0.1.47 新增 |
| `STRATA_MMQ_TAB` | — | OFF | 0.1.47 新增 |
| `STRATA_PARITY_GFX1100_QSA_SCORES` | — | OFF | 0.1.47 新增 |
| `STRATA_ISA_FLOOR` / `PORTABLE` / `WERROR` / `BUILD_TESTS` | 空 / OFF / OFF / OFF | 同 | 同 |

**=>  0.1.42 显式传的项，在 0.1.47 全部是默认值（CMakeCache 逐项已证）。没有任何一项"上游最佳实践漏了、需要我们从 0.1.42 补回来"。**

唯一可回退项 `-DSTRATA_Q6K_EXPERTS=OFF`，其 CMake 注释逐字：

> `On by default since MODEL-UPDATE Phase 1: one more instance per grouped kernel in iq_kernels.cu, +19 KB of sm_60 code, measured to leave every expert-cache slot count as it was (P100, R9700). -DSTRATA_Q6K_EXPERTS=OFF drops it.`

=>  只多一个 Q6_K kernel 实例，**"slot count 不变"由上游实测背书**，对 IQ4_XS 无用也无害；关掉只省 19 KB 代码和编译时间，**无性能收益**。

## 2 三个"看起来像解药"的开关，全部源码级否决

### 2.1 `STRATA_PREFILL_MMQ`（HIP 预填 MMQ）
`CMakeLists.txt` 门控原文：

```cmake
option(STRATA_PREFILL_MMQ "Build the optional GGML MMQ prefill path for HIP" OFF)
if(STRATA_PREFILL_MMQ AND NOT STRATA_ENABLE_HIP)
  message(FATAL_ERROR "STRATA_PREFILL_MMQ requires STRATA_ENABLE_HIP=ON")
endif()
```

而同一段上方写死：`STRATA_HIP_GFX906` 与 `STRATA_ENABLE_HIP` 是两套后端、只能开一个。
**我们走 `STRATA_HIP_GFX906=ON` =>  打开 PREFILL_MMQ 会在 configure 阶段 FATAL_ERROR。**

另有 `if(STRATA_PREFILL_MMQ AND NOT STRATA_NATIVE_EXPERTS)` 的第二个 FATAL_ERROR（这条我们满足）。

### 2.2 `STRATA_MMQ_TAB`（指针表预填 MMQ）
注释逐字：`CUDA only (not HIP, not gfx906)`。**明确排除 gfx906。**

### 2.3 `--prefill-pipe`
help 原文：

```
--prefill-pipe R   opt-in, a layer split: prompt chunks sized so the stages read at once - R is
                   this PC's b/a in tokens (setup's --calibrate measures it)
```

**前提是 layer split（多卡层切分）。我们单卡，无 split =>  不适用。**

## 3 两个运行时"看着能救预填"的候选，都已被实测/上游量化否决

### 3.1 `--pcie-frac`：测过，**预填不变**
- 源码：`generate.cpp:680` 注释 `< 0: the model's default (0.2 direct for the Q2_0 pack, 0.55 DMA for native packs)` —— 我们 native pack 默认应 0.55，生产设 0.20（**只有默认的 36%**）。
- 但 `pcie_frac` 的作用面是 **verify window（decode 的 MTP 验证窗口）**：`verify.hpp:327` 逐字 *"The GPU plan the pool writes each layer (VRAM hits + the PCIe share of the misses)"*；预填走 `src/prefill/`，是另一条路。
- 历史实测（register `P25`，929 s calibrate）：
  `0.00=35.19 / 0.20=35.68 / 0.35=32.76 / 0.36=33.71 / 0.55=30.95 / 0.75=29.05`，并明确记录 **`预填不变(455.55/455.80)`**。
- =>  **「提高 pcie-frac 能让 GPU 参与预填」这个推断被实测否定**，0.20 是 decode 最优（+10.9%，独立复核 +9.0%）。

### 3.2 `--prefill auto:16384`：上游已量化，**牺牲 ring 更值**
help 原文：`auto = the largest chunk up to 8192 whose buffers the expert cache can lend`。
源码注释（`generate.cpp:7576-7583`）逐字量化：

> `The chunk and the ring are one budget, and the ring is the better buy. ... on a 120K prompt: 8960 tokens with the 17-slot ring that leaves reads at 963 tok/s, 8192/130 at 1,008, 7168 with the ring full at its 199-slot byte budget at 1,000, and 5632/199 at 915. A ring slot is worth ~0.53 tok/s there and a chunk token ~0.05`

=>  加大 chunk 会挤掉 ring 槽，**每挤掉一个 ring 槽损失 0.53 tok/s，而每加一个 chunk token 只赚 0.05 tok/s**。auto 的算法本身就是"取最大的、且仍让 ring 满的 chunk"。
**=>  auto:16384 是负收益，不是候选。**

## 4 那"预填期 GPU 0%"到底受什么限制

生产启动行（实读）：

```
strata: prefill plan: chunk 8192, ring 96 kept: file set 0.4 GiB fits the page cache 78.8 GiB
        -> about 0.0 GB read from the drive per 32768-token prompt (4 chunks)
strata: prefill plan inputs: 55.4 GiB experts, 22.0 GiB in the GPU caches, 36.9 GiB RAM copy
        (1554 lend slots kept), file tier 0.0 GiB; 78.8 GiB available for the page cache; PCIe 12.0 GB/s
```

- 专家总量 **55.4 GiB**，GPU caches 只能装 **22.0 GiB（39.7%）**，其余 **36.9 GiB 在 RAM**。
- 预填每个 chunk 都要过所有层的所有专家 =>  **60% 的专家只能由 CPU pool 算**（`native_expert_grouped` 的 CPU 侧）。
- GPU 在预填期只承担 attention（`qsa_prompt_attn`），占墙钟比例 < 1% =>  20 s 采样的 `gpu_busy_percent` 显示 **0.0**。

**这是「专家总量 55.4 GiB vs VRAM 可装 22 GiB」的硬边界。** 没有任何编译开关或运行时 switch 能绕开——除非减小专家总量（换量化 = 改答案）或换更大显存的卡。

## 5 结论（可直接执行的部分）

| 层 | 结论 |
|---|---|
| 编译开关 | **无需补任何项**。0.1.42 的显式项在 0.1.47 都是默认。唯一可选 `-DSTRATA_Q6K_EXPERTS=OFF`（无性能收益） |
| 预填加速（GPU 化） | **无可用开关**。PREFILL_MMQ/MMQ_TAB 被 gfx906 排除；prefill-pipe 需多卡；pcie-frac 实测预填不变；大 chunk 被上游量化否决 |
| 预填加速（减少重算） | 唯一的已实现项就是 `--resident-experts` + B7（file tier 归零），**已在用** |
| decode 加速 | 0.20 已是实测最优（+10.9%/+9.0%） |

## 6 尚未测过的两个（标注不确定性，不建议优先）

1. **`--prefill-head-alias`**：`generate.cpp:758` 注释 `lend the native output head's VRAM to prompt buffers between request phases`。
   理论上能给 prompt buffer 多一点 VRAM，但原文限定 **"between request phases"**（请求之间），对**单请求内的预填**可能无效。
2. **`STRATA_PREFILL_RING`**：手动钉 ring 槽数做 A/B。当前 auto 给 96 槽；若 ring 不是瓶颈，手调无意义。属诊断用途，非收益杠杆。

两项都需发车验证，且预期收益低；在 §5 的硬边界未变之前，优先级低于"保持现状"。
