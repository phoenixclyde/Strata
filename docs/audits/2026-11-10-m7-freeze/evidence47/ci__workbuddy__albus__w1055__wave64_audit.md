# wave64 硬件级专属代码审计（R52 核查）

远程树：`/home/albus/strata166/pr/k10`（src/ + include/，658 个源文件）。只读 grep/sed，未改任何远程文件。
原始证据：`remote_grep_raw.txt` / `remote_ctx2~5.txt`（同目录）。

## 0. 前提：项目有一个「逻辑 warp 契约」

`include/strata/platform/hip_compat/strata_hip.h:7-17`（gfx906 HIP 构建的兼容层，放在 include 路径首位）：

> 每个内核按 32-lane CUDA warp 写。gfx906 是 64-lane wavefront，这里一个 CUDA warp = wavefront 的**逻辑 32-lane 半波**：所有 shuffle 默认 width=32（`STRATA_SHFL_W_DEFAULT=32`，:216），`__ballot_sync` 返回调用者所在半波的 32 位掩码（:220-224），`__syncwarp` = 整波 barrier + LDS fence（:227-232）。

即：块内 `warp = t >> 5`、`lane = t & 31` 在 gfx906 上是**逻辑半波**；`THREADS/32` 数出的是逻辑 warp 数（= THREADS/32 对任何 64 的倍数成立，因为一个 wave64 恰含 2 个逻辑 warp）。该文件只重映射 `__shfl*_sync` 系列；**不带 _sync 的原生 `__shfl_xor(v, o, 64)`（width=64）不受影响，是真正的 64-lane 硬件交换**。`program/generate.cpp:3964` 另有门禁：gfx906 构建的内核假设 64-lane 波，wave32 卡直接拒启。

---

## §1 波数/占用率计算逐点表（Q1a 全量 55 处 + 关键补充）

判定基准：`THREADS/32` 类计算在逻辑 warp 契约下**按设计正确**；只有脱离该契约（原生 64 位 match 掩码、跨半波假设）才算真错。

| 文件:行 | 代码 | 判定 | 理由 |
|---|---|---|---|
| bf16_gemv.cu:137,157,172 | `warps = THREADS/32` | 无害 | 逻辑 warp 数，launch/循环步长，契约下自洽 |
| cvec.cu:72,78 | `part[THREADS/32]`；`lane < THREADS/32` | 无害 | LDS 槽 = 逻辑 warp 数；归约走 width-32 shuffle |
| gr.cu:42 | `WARPS = THREADS/32` | 无害 | 同上（:188-222 的 occupancy 注释为测量记录） |
| iq_kernels.cu:6763 | `r += WG_THREADS/32` | 无害 | `warp` 是逻辑索引，步长一致 |
| native_qsa_indexer.cu:88,180 | `lane < THREADS/32 ? partials[lane]` | 无害 | 槽数=逻辑 warp 数，随后 width-32 归约 |
| qsa_pattn.cu:63 | `WARPS = THREADS/32` | 无害 | 同上 |
| qsa_prompt_attn.cu:112,1510 | `float qmax[THREADS/32]` | 无害 | 每逻辑 warp 一个 max 槽，块内合并 |
| router_top10.cu:77-78,288-289 | `s_red[RT_MAX_THREADS/32]` 等 | 无害 | 同上；gfx906 上块内核已被 wave 内核替代为默认（:463） |
| s2_expert_grouped.cu:581,607,632,1302 | `warps = THREADS/32` | 无害 | 同上 |
| fused_gr.cu:46,650 | `WARPS = THREADS/32`；`Q32_WARPS` | 无害 | 同上 |
| qsa_decode_attn.cu:27-28 | `THREADS=256; WARPS=THREADS/32` | 无害 | 256 线程 = 4 wave64 = 8 逻辑 warp；:143 `warp=t>>5, lane=t&31` 全文一致 |
| attn_prompt.cuh:18-19,123 | `AP_THREADS/32 * ...` static_assert 与循环 | 无害 | 逻辑 warp 几何，编译期断言自洽 |
| dense.cuh:27,196 / kernels.cu:2141,2307,2390 / moe.cuh:494,530 / moe_q4k.cuh:132 | `Q8S_THREADS/32`（grid 行分块） | 无害 | 行/线程分组，不依赖物理波宽 |
| gdn_core.cuh:58,119,193,205 / gdn_prompt.cuh:76,147 | `red[GDN_THREADS/32][...]` | 无害 | LDS 槽数=逻辑 warp 数 |
| moe.cuh:13,88,132,319,397 | `RR_THREADS/32` 等 | 无害 | 同上 |
| moe_mma.cuh:305-306 | `WR=BM/32, WT=MM_THREADS/32/WR` + static_assert "warp layout" | 无害 | 逻辑 warp 平铺 |
| prefill.cu:107,147,158,258,268 | `HCB_THREADS/32` 等 | 无害 | 同上 |
| topk.cuh:93,111（split 路径） | `warp_n[TOPK_THREADS/32]`、`warp=tid>>5` + `__ballot_sync` | 无害 | ballot 被兼容层映射为半波掩码，逻辑自洽 |
| dflash2.cpp:280,282,455 | `5*N_/32*8`、`N_/32` | 无害 | 位平面/字节几何，与波无关 |
| moe_mmq.cu:184 | `__shfl_xor_sync(..., 32/8, WARP_SIZE)` | 无害 | width 显式 32；这是全树唯一 `WARP_SIZE` 使用点 |
| **topk.cuh:51 / qsa.cuh:240（split 路径）** | `(unsigned) __match_any_sync(0xffffffffull, bin)` | **疑似真错（可达性待查）** | 见下文专段 |
| qsa_select.cu:1454 | `__match_any_sync(0xffffffffu, bin)` | 无害（gfx906 不可达） | 位于 block_topk_cluster_kernel（:1406），要求 `ptxVersion>=90` + cluster launch（:2395-2434），仅 CUDA sm90+ |
| 各处 `cudaOccupancyMaxActiveBlocksPerMultiprocessor`（ds4_iq.cu:1140、moe_fused.cu:638-666、moe_fused_iq.cu:1709 等 ~15 处） | 运行时占用查询 | 无害 | API 按当前架构计算，无 wave32 假设 |

**疑似真错专段：split 路径 radix select 的 match_any**
`src/split/src/topk.cuh:51` 与 `src/split/src/qsa.cuh:240`（`#if FNX_HIP` 分支，注释 "HIP wants a 64-bit mask (wave32: the high half is empty)"）。机制：wave64 上 64 位掩码让 match 跨**整个 wavefront（2 个逻辑 warp）**匹配；结果被 `(unsigned)` 截断只保留位 0-31。同 bin 组若只落在第二个半波，`peers32==0`、`__ffs(0)==0`，`lane == ffs-1` 永假 → 该组**一次原子都不发**，hist 漏计整组；若两个半波都有，`__popc(peers32)` 只计第一个半波 → 漏计一半。两种情况 radix 阈值都可能错。缓解因素：该代码只出现在 `src/split/src/`（FNX_HIP 构建注记指向 r9700/RDNA 实验，split/src/hip/mma.h 是 wave32 WMMA shim），split 源码内无任何 `STRATA_HIP_GFX906` 守卫——**若 split 路径确实只编给 RDNA wave32 卡则无害，需查构建系统确认**。

---

## §2 wave64 硬件用法清单（gfx906 实际在跑）

| 内核 | 指令/机制 | 用途 | 64-lane 正确？ |
|---|---|---|---|
| `native_mmvq_wave_kernel`（native_mmvq.cu:2402-2453，`STRATA_HIP_GFX906` 门控，`STRATA_MMVQ_WAVE` 默认开） | 每 R 行一个 wavefront，块=4 wave（256 线程）；**`__shfl_xor(v, off, 64)` 全波蝶形**（:2443）；`static_assert(64 % F::T == 0)`（:2418） | q8 MMVQ 行积和，替代每行一块的 LDS+syncthreads 布局；W862 实测 R 表（:2368-2378） | ✅ 原生 width-64 shuffle，lane `&63`、`>>6` |
| `router_top10_wave_kernel`（router_top10.cu:198-，gfx906 默认，:463） | 64 线程/块=1 wavefront；**width-64 蝶形 argmax**（:216,248-249）；无 LDS 往返、无块 barrier | 每 token 单波 top-k 路由，与块内核逐位一致 | ✅ |
| `row_dot64`（iq_kernels.cu:5574-5589，STRATA_EXP_MODE=1 "W64"） | 每行一个 64-lane wavefront，**`__shfl_xor(s, o, 64)` 64-lane 蝶形**（:5588）；非 HIP 分支 `__trap()`（:5590） | 分组专家的 wave64 布局（gfx906 默认模式为 7，W64 为可选项） | ✅ |
| `xor8` / `gr_up_fast_kernel` / `gr_down_split_kernel`（fused_gr.cu:1819-1826,1908-1946） | 8-lane 组内 `__shfl_xor(v, o, 64)`；down-split `__launch_bounds__(GS_WAVES*64)` + width-64 蝶形（:1946） | GR up/down 的波级归约 | ✅ |
| `__syncwarp` 实现（strata_hip.h:227-232） | `__builtin_amdgcn_fence(RELEASE/ACQUIRE, "wavefront")` + `wave_barrier` | 逻辑 warp 同步的硬件底座（整波 barrier + fence） | ✅ |
| moe_f16_common.cuh:240,246 | 裸 `__builtin_amdgcn_wave_barrier()` | 波级到达栅（过同步安全） | ✅ |
| qsa_decode_attn gfx906 查询重排路径（:332-347,356-393；`STRATA_GFX906_ATTN_QUERY_SWIZZLE` 默认 arch_defaults.cpp:218=1） + `reduce12_gfx906`（:94-117） | q 侧 LDS 双射重排 + width-32（逻辑 warp）`__shfl_xor_sync` 蝶形 | INT8 attention 打分归约；**"swizzle" 是 LDS 布局置换，不是 ds_swizzle 指令** | ✅（逻辑 warp 语义，契约内） |

**要点**：全树 **0 处** `ds_swizzle/ds_bpermute/ds_permute` 指令使用（仅 3 处注释提及为何弃用：qsa_decode_attn.cu:460,471、s26_tsum.cuh:7）。**DPP（mov_dpp row_xmask / permlanex16）只存在于 wave32-RDNA 代码**，均被 `!defined(STRATA_HIP_GFX906)` 排除（qsa_decode_attn.cu:150-162、s26_tsum.cuh:14-22）。gfx906 的跨 lane 硬件通道 = 原生 `__shfl*`（width 32 逻辑 / 64 全波）+ wave_barrier/fence + `v_perm_b32`（`__byte_perm`→`__builtin_amdgcn_perm`，strata_hip.h:314-318，纯 lane 内字节置换，与波宽无关）。`__builtin_amdgcn_wmma_*_w32` 是 gfx11/gfx12 wave32 矩阵核，gfx906 无此硬件（CDNA 用 MFMA，本树未用）。

---

## §3 wave32 专用代码清单（gfx906 上不可达/默认关闭）

| 位置 | 内容 | gfx906 隔离方式 |
|---|---|---|
| verify_kernels.cu:832 起 | wave32 取样/argmax/top-k 内核族（CUDA + RDNA HIP） | `#if !defined(STRATA_HIP_GFX906)` |
| qsa_decode_attn.cu:150-543（pre75/DPP 族，`shfl_x<DPP>`、`warp_sum_x`、`reduce12<DPP>`） | DPP row_xmask + v_permlanex16 蝶形，gfx103x RDNA2 专用 | `STRATA_ATTN_PRE75_BUILT` 要求 `!defined(STRATA_HIP_GFX906)` |
| s26_tsum.cuh:14-22 | permlanex16 / update_dpp row_xmask | `defined(__HIP_PLATFORM_AMD__) && !defined(STRATA_HIP_GFX906)`（注释：gfx10+ only） |
| router_top10.cu S6 内核（launch_generic，:427 注释 "wave32-shaped"） | 波形 32 的路由内核 | gfx906 默认不走，需 `STRATA_HIP_ROUTER_FAST=1` |
| split/src/hip/mma.h + moe_mma.cuh + qsa_prompt_attn.cu:1938-1944 + qsa_select.cu:333 + prefill 各 wmma 文件 | `v_wmma_*_w32`（gfx11/gfx12 wave32 矩阵核；非 gfx11/12 分支 `__builtin_trap()`） | 架构宏门控；gfx906 无 WMMA |
| qsa_select.cu:703,1222 等注释、moe_fused_iq.cu:1194-1203 | RDNA/wave32 测量注记 | 仅注释 |
| device.cu:62 / device.hpp:33 | wave32 HIP 后端拒收 wave64 卡的报错 | 对端门禁（wave32 后端侧） |

---

## §4 结论（三句）

1. **有，但形态单一**：gfx906 的 wave64 硬件级专属代码 = 4 组「整波一工作单元 + 原生 width-64 `__shfl_xor` 蝶形」内核（native_mmvq wave、router_top10_wave、iq_kernels W64、fused_gr down-split/up-fast），外加兼容层的 wavefront fence/barrier 底座；**没有任何 DPP 或 ds_swizzle 指令用法**——最接近的 DPP/permlanex16 都在 `!STRATA_HIP_GFX906` 的 wave32-RDNA 代码里。
2. **最成熟的是 `native_mmvq_wave_kernel`**（STRATA_HIP_GFX906 专属布局 + 64%T static_assert + 实测 R 表 + 环境开关），`router_top10_wave_kernel` 次之（gfx906 默认路径、逐位一致论证完整）。
3. **R52 的 "wave32 假设" 基本不成立**：全部 ~55 处 `THREADS/32` 都在 strata_hip.h 的「逻辑 32-lane 半波」契约内，gfx906 上按设计正确（width-32 shuffle/半波 ballot 恰好把波切成两个逻辑 warp）；唯二的脱离契约点是 split 路径的 `__match_any_sync(0xffffffffull)`（topk.cuh:51、qsa.cuh:240，64 位掩码在 wave64 上跨全波匹配 + `(unsigned)` 截断会漏计直方图——但该路径疑似仅 RDNA 构建，需查构建系统确认），以及 qsa_select.cu:1454 的 32 位掩码（sm90-only cluster 内核，gfx906 不可达）。
