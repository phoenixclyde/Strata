# W893 · ki 的 gfx906 vLLM 内核库对账，以及被漏掉的 wave64

> **【更正 2026-11-03 01:1x，W901】** 本件把“30 个内核按 `WARP=32` 记账”写成了**漏项/浪费**，这是错的。
> `strata_hip.h` 的契约是“**逻辑 32-lane warp**”，垫片把每次 shuffle 的默认宽度设为 **32**（不是 warpSize=64），
> 并在硬件上实测成立（width32 时高半组取本组 lane31=物理 63）。⇒ 32 记账**是设计**，不是缺陷；
> 真正的债只有一条：mask 被垫片丢弃，而 HIP 7.14 要求 64 位 mask。详见 `W901_WAVE64_ACCOUNTING.md`。


> **[部分撤回 · 2026-11-02 23:0x，AUDIT23 P0-1]** §0 第 2 条「**CK 不是 MI50 的路**」只查了 `ROCm/composable_kernel`
> 的 **GitHub 主线**（`d84d8e2` 0 处 gfx906），**没有查我们自己装的那份**：宿主 `composablekernel-dev 1.1.0.60404`
> 有 **17 处** gfx906（全在 `device_*_dl.hpp`，DL 点积路线）。生产容器则**根本没装 CK**。
> ⇒ 正确表述见 `W894 §1`：「主线已无 gfx906」成立，「我们没有」不成立；**CK 对 decode 仍无直接用处**（不吃 Q4_K/Q8_1）。
> 本件其余结论（wave64 硬件事实、ki 内核清单、半波 2×）不受影响。

**来源**：166 上的 `KIntegrated/vllm-gfx906-mobydick` 源码（`/home/albus/routeK/base/ki030-main`，HEAD `6ccbb03119`，2026-09-27）、
`ROCm/composable_kernel` 主线（`d84d8e2`，本机 sparse clone）、本 fork 源码、ROCm/LLVM 官方设备属性。
**方法**：只读源码与文档、只做独立编译探测；**生产零改动、零重启**。所有数字标明是「源码注释里的实测」还是「本轮现算」。

---

## 0 结论先行

1. **「vLLM 要看 ki 的库」成立，而且源码就在 166 上**：`ki030-main` 就是专为 gfx906 改的 vLLM fork
   （`csrc/rocm/*_gfx906.cu` + `csrc/gfx906_fa/` + `docs/gfx906/` 60 余篇 devlog）。
   上游 vLLM 侧有明确记录 **gfx906 不受支持**（vllm#33811「Add comments explaining gfx906 (MI50/MI60) is not supported」），
   所以这一层只能看 fork，不能等上游。
2. **CK 不是 MI50 的路**：`ROCm/composable_kernel@d84d8e2` 的 `GPU_TARGETS` 只有
   `gfx908;gfx90a;gfx942;gfx950;gfx1030;gfx11xx;gfx12xx`，全仓库 `gfx906` 引用数 **0**。
   CK 的算子建立在 MFMA 上，gfx906 没有 MFMA ⇒ 没有「可移植的 CK 加速库」。这解释了 ki 为什么手写 HIP 内核。
3. **wave64 是上几轮的漏项，而且它会改结论**：gfx906 是 64 lane/波、**40 波/CU**、2560 work-item/CU。
   我们全部内核都是按 `WARP = 32` 写的，`THREADS/32` 数出来的「warps」在硬件上是**半个波**。
   换成波口径后，占用率、每波行数、归约宽度三件事都要重算；ki 有三处实测直接钉住这一点（§2）。
4. **真正可抄的不是指令，是四件调度/形状的做法**：全波线程数、16B 向量载入、**按文件**开 `max-ilp`、
   decode attention 的「头打包 + KV 切分」网格。四条都不需要重写算法，其中两条零停机就能验证。
5. **`v_dot8` 继续不做**：ki 自己的 T5 也只停在「先做 P3a 探针」，且它的可用格式是 AWQ/GPTQ W4A16 + `v_dot2_f32_f16`，
   不是我们的 Q4_K×Q8_1。与 R47 DONE_NEG 的结论一致。

---

## 1 ki 的 gfx906 内核清单（源码级）

| 文件 | 行数 | 形态 | 源码里记录的实测 / 结论 |
|---|---|---|---|
| `csrc/rocm/dense_gemv_gfx906.cu` | 1394 | M=1 W16A16 GEMV，行并行；每线程 16B（8 half）沿 K，`__ockl_fdot2`；KCHUNK 512/1024/2048/4096 → 64/128/256/512 线程 = **1/2/4/8 个波** | 大行（K=5120/lm_head）**3114 vs 3128 µs，≈98% of HBM floor**，判「内核已到内存地板」；M=1 时 K-split 比单遍慢 **2.4–4.2×**（CAS+zero+小块的启动成本）；小行（GDN-small/shared down）3.6–14× floor 属**启动/延迟受限**，不是占用率问题 |
| `csrc/rocm/moe_q_gemm_gfx906.cu` | 910 | 融合 MoE W4A16 GEMM；`THREADS_X=256`（源码逐字注：**4 waves on wave64**），`BLOCK_KN_SIZE=256`，每线程 4/2 列，packed 64-bit CAS 累加 | 与 `moe_q_gemm_rdna3.cu` 同族；wave32 版按 8 waves 算，wave64 版按 4 waves 算——**同一个 256 线程块，两种波口径** |
| `csrc/rocm/moe_align_m1_gfx906.cu` | 173 | M=1 的专家对齐/计数 | — |
| `csrc/gfx906_fa/kernel/fattn-q8.cuh` | 1273 | decode/prefill FA，Q8 K + fp16 V（取自 ggml 的 fattn 血统） | B=1 decode：**16 blocks = 6.7% 的波槽**；头打包 NC2=8 + KV 切分 y=16 后 **245 → 58.3 µs（4.2×）**，服务端 57.1→62.7 t/s（+9.8%）；y=32/64 反而退化 |
| `csrc/gfx906_fa/kernel/fattn-q8-paged.cuh` | 768 | paged KV 的 FA | V2 版 416 个 workgroup 与 MoE/GDN 共驻被挤，服务端退化 7×（285 vs 42 µs）⇒ 网格形状是**服务端**的一等变量 |
| `csrc/rocm/skinny_gemms.cu` | ~2400 | M≤16 的 skinny GEMM，含 int4 | 全局 `max-ilp` 下 MoE **−2.2%**，per-file 才两头都赚（§4） |

**`docs/gfx906/DEAD-ENDS-AUDIT.md` 的硬件常量（rocminfo 实测）**：60 CU × 4 SIMD、wavefront 64、
`maxThreadsPerCU=2560`（**40 waves/CU**）、`regsPerBlock=65536`、LDS/block 65536 B。
同一份审计把 11 条死路逐条反编译读 HSA notes：**`vgpr_spill_count` 全是 0**、VGPR 12–79
⇒ 它们不是被寄存器压死的，死因是 HBM 地板、孤立→服务的「transfer flip」、结构取舍、网格形状、Triton 代码生成。

---

## 2 wave64 的三条硬事实（这是此前漏掉的部分）

| # | 事实 | 外部/源码依据 | 对我们的意义 |
|---|---|---|---|
| W1 | **gfx906 一个波 = 64 lane，一颗 CU 最多 40 个波**（4 个 SIMD × 10） | ROCm GCN5.1 设备属性与 LLVM `libomptarget` 输出：`Wavefront Size: 64`、`Max Waves Per CU: 40`、`Max Work-item Per CU: 2560`；ki `DEAD-ENDS-AUDIT` 同值 | 我们的 `THREADS/32` 是**逻辑 warp 数**，不是波数。256 线程块 = **4 波**，不是 8 波；占用率上限 = `blocks/CU × THREADS/64 / 40` |
| W2 | **归约的蝶形必须从 mask=32 起，且 32 lane 一组只在自身半波内闭合** | ki `DEVLOG-fp16-skinny.md`：v1 从 `mask = NV/2` 起步，**丢掉半波的部分和**，M=8/16 输出偏 2.0–2.8 | 我们的 `for (off = WARP/2; off; off >>= 1)`（`WARP=32`）在 `off ≤ 16` 时只读同半波的 lane，**求和是对的**；但 `__shfl_*_sync(0xFFFFFFFF, …)` 的 mask 只有低 32 lane，在 wave64 上属掩码外调用（AMD 忽略 mask 才没出事）——是**可移植性债，不是现行 bug** |
| W3 | **半波块 ≈ 全波块的 2× 差**（同块数、同流长，只改波配置） | ki `DEVLOG-moe-c2v.md`：v1a 32 线程（**半个波**）117.2–117.4 µs vs v1b 64 线程（**一个波**）59.0 µs | 任何 `blockDim = 32` 的 launch 在 gfx906 上都是「占一个波槽只干一半活」。我们的 `bf16_gemv_split` 在 `TPR=32` 时正是这个形状 |

补充一条与本机直接相关的：**Triton 的 `getWarpSize` 默认返回 32**，gfx906 必须返回 64（ki `RECON-triton-1.md`）。
上游从 **v3.8.0 的 `ISAFamily::GCN5_1`（PR #9628）** 才原生支持，且 DPP broadcast 打开、
`supportsDirectToLdsLoadBitWidth` 仍缺 gfx906 的 32-bit 直通。我们不跑 Triton 路线，这条只作外证。

---

## 3 我们自己的波口径审计（现读源码，本轮现算）

| 内核 | 线程/块 | 物理波/块 | 代码里的「warp」 | 每波行数 | 备注 |
|---|---|---|---|---|---|
| `native_mmvq.cu` | `WARPS*WARP = 128` | **2** | 4 个（虚） | `ROWS = SmallK ? 4 : 1` ⇒ SmallK 时 **2 行/波** | `__launch_bounds__(128,1)`；4 个虚 warp 挤 2 个波 |
| `qsa_decode_attn.cu` | 256 | **4** | 8 个（虚） | 按 chunk/head 分波 | `grid(n_chunks, n_head_kv, n_q)`：短上下文时 n_chunks 小 ⇒ **块数可能远低于 2400 个波槽**，与 ki 的「16 blocks = 6.7%」同型风险 |
| `qsa_prompt_attn.cu` | 128 | **2** | 4 个（虚） | cell 8/线程 | 逐字注「4 warps」，实为 2 波 |
| `fused_gr.cu` | 256 | **4** | 8 个（虚） | — | `part[WARPS][HC]` 是 8 份 LDS 部分和 ⇒ 实际 8 个半波各写一份 |
| `bf16_gemv`（warp 版） | 256 | **4** | 8 个（虚），`lane = tid & 31` | **2 行/波** | 每次 load 32 lane × 2 B = **64 B**；全波本可 128 B |
| `bf16_gemv_split`（router 走这条的 TPR 变体） | **TPR=32** | **1** | 1 个 | 1 行/块 | **块占用一整波、只用 32 lane**；`PROJECT_BF16` 的 `constexpr int TPR = 32` |
| router 实际入口 `bf16_gemv_fp32_mmvf_multi` | 256（`mmvf_block_size(2560)` 选 256） | **4** | 8 个（虚） | 1 行/块 | `grid = n_out = 512` ⇒ 512/60 ≈ 8.5 块/CU ≈ **34 波/CU ≈ 85% 波占用** |

**这张表推翻了我上一轮给 R50 的隐含归因**：router 的 60 GB/s **不能**归到「半波/低占用」上——
它的入口是 256 线程、85% 波占用。60 GB/s 是「独立链路相减」得到的派生量（43.54 µs/层），
而 2.62 MB / 43.54 µs 与 512 块 × 5 迭代的规模不相称。
⇒ **R50 的第一步必须是单内核独立计时**（ki 的规矩也是「先 standalone，再 serve A/B」），先证伪再改内核。

---

## 4 四处对照与可执行动作

| 对照项 | ki 的做法（源码） | 我们的现状 | 动作 |
|---|---|---|---|
| M=1 GEMV 的载入宽度 | 每线程 16B（8 half）沿 K 连续，`__ockl_fdot2`；RPT 行/线程；KCHUNK=K 单遍 | `bf16_gemv_split` 每线程 2B 标量、TPR=32 | R50 的候选形态：**16B 载入 + 全波 TPR=64/128**，先证 60 GB/s 是真的 |
| 编译期 ILP | `-mllvm -amdgpu-sched-strategy=max-ilp`，**只给 W4/FA/skinny 这几个文件**；全局套用 MoE −2.2% | `build.ninja` 里 **0 条 `-mllvm`** | R49 具体化为：per-file 开该开关，先汇编 diff 再微基准。本轮已在 166 验证：**开关能改代码生成（同一 kernel 汇编差 66 行）**，不是无效参数 |
| decode attention 的网格 | NC2 头打包 + `gridDim.y` KV 切分；16 块→6.7% 波槽→4.2× | `grid(n_chunks, n_head_kv, n_q)`，短上下文块数少 | R52 里一并量「活跃波槽占比」，别只量 ms |
| 专家 GEMM 的波配置 | 256 线程 = 4 波；半波 vs 全波 2× | `native_mmvq` 128 线程 = 2 波、SmallK 2 行/波 | 已由 R23 的行数表覆盖，**不重开**；只把波口径写进台账，避免以后再按 32 算 |

**不采纳**：CK 移植（无 gfx906）、Triton 路线（我们不用 Triton）、`v_dot8`（格式不符 + ALU 非瓶颈，R47 已结）、
ki 的 AWQ/GPTQ W4A16 权重格式（我们是 Q4_K/Q5_K + Q8_1 激活，换格式等于换数值契约）。

---

## 5 队列变更

- **R52（新增，零停服）**：wave64 归约与波槽审计 —— ①把每个内核的 `THREADS/32` 换算成真实波数并记账；
  ②逐个确认归约在 `off ≤ 16` 时只在半波内闭合（W2），把 `__shfl_*_sync` 的 32-bit mask 列为可移植性债；
  ③量 decode attention 的**活跃波槽占比**（不是 ms）；④只输出「哪些 launch 的块数 < 2400 波槽」清单。
  不改生产；发现真 bug 才升级为停机项。
- **R49（细化）**：从「软件流水/ILP 探针」具体化为 **per-file `-mllvm -amdgpu-sched-strategy=max-ilp`**：
  先在 `native_mmvq.cu` / `bf16_gemv*` 上做汇编 diff（本轮已验证开关有效），再独立微基准，
  最后才谈服务 A/B；预期方向按 ki 的证据是「dense 赚、MoE 亏」，**必须按内核分别判**。
- **R50（修正判据）**：加一条前置门 —— **单内核独立计时必须复现 ~43.5 µs/层**，否则 60 GB/s 是派生假象，条目按 DONE_NEG 关。

---

## 6 复现

```bash
# ki 源码与内核
ls /home/albus/routeK/base/ki030-main/csrc/rocm/*gfx906* /home/albus/routeK/base/ki030-main/csrc/gfx906_fa/kernel/
sed -n '1,30p' /home/albus/routeK/base/ki030-main/csrc/rocm/moe_q_gemm_gfx906.cu   # 4 waves on wave64
# 硬件属性
/opt/rocm/bin/rocminfo | grep -E 'Wavefront Size|Max Waves Per CU|Max Work-item'
# max-ilp 开关是否有效（本轮实测：汇编差 66 行）
/opt/rocm/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 -S k.cu -o plain.s
/opt/rocm/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 \
  -mllvm -amdgpu-sched-strategy=max-ilp -S k.cu -o ilp.s && diff plain.s ilp.s | grep -c '^[<>]'
# CK 无 gfx906
grep -rn 'gfx906' albus/w896/forks/ck/include albus/w896/forks/ck/library | wc -l   # 0
```
