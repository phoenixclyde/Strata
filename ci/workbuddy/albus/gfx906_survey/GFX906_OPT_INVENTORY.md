# gfx906（MI50/MI60/Vega20）优化代码全清单：三源逐文件盘点

> 出具 2026-11-07 05:5x。口径：**源码级**（下载完整树、给行号）> **API 级**（PR/issue 编号 + merge 状态）> **自述级**（README/DEVLOG，标注"未复现"）。
> 上游基准：`ggml-org/llama.cpp` master `669204ee2b9004845b34f26466a91d003edc98aa`（2026-11-06 19:53Z）。
> KI 基准：`KIntegrated/vllm-gfx906-mobydick` 分支 `gfx906/main`（2026-10-26 push，40.4 MB tarball）。
> 生产未改动，本轮零停服。

---

## 0 摘要（结论先行）

| # | 结论 | 证据 |
|---|---|---|
| 1 | **gfx906 的指令前提**：`v_dot4_i32_i8`（dp4a）/`v_dot2_f32_f16`/`v_dot8_i32_i4` 可用；`v_dot4c/dot8c` **不可用**；**无 MFMA、无 WMMA、无 bf16 硬件** | 上游 `common.cuh:722-724` 与 `common.cuh:771-773` 直接把 `__gfx906__` 写进 dp4a 与 dot2 的可用分支；KI `dequant-instructions.md` 同结论；W835 已用 `llvm-mc -mcpu=gfx906` 实测 |
| 2 | **KI 是 gfx906 上做得最深的一份代码**：不只是"几个 kernel"，是**整套 attention 后端 + MoE grouped GEMM + dense GEMV 家族 + 逐文件编译策略 + 一整套负结果台账** | `docs/gfx906/README.md` §What changed 六节、`CHANGELOG.md` 202 行、`DEAD-ENDS.md`、65 个源码文件引用 gfx906 |
| 3 | **上游 llama.cpp 对 gfx906 是"能用+局部调过"，不是"专项优化"**：全文只有 **5 处** `gfx906` 字面，但通过 `GCN`/`CC_VEGA20`/`CC_IS_GCN` 三套谓词间接覆盖到 10 条路径 | `grep -rn gfx906` 全树 = 5 |
| 4 | **上游最近三个月才补上 gfx906 的 MMQ tile 表**（#27841，2026-08-28 merged，+281 行新建 `mmq-config-gcn.cuh`），在此之前 gfx906 走的是"通用/别的架构"的表 | PR #27841 files |
| 5 | **上游有一个尚未修的 gfx906 回归**：#29948 的 grid 顺序使 gfx906 **MoE prefill −15~50%**（OLMoE pp512 −43%、gemma-4 pp512 −50%），issue #31599 仍 open，报告人自带了"GCN 保留旧序"的补丁 | issue #31599 正文 |
| 6 | **fork 生态已形成谱系**：`iacopPBK → {fuutott, eslowney} → mxxm-t/mx-llama.cpp`，另有两支独立线（`exabit-io` 的 4×Vega20 调优+补丁系列、`marcelromano` 的 wave64 内核）。**iacopPBK README 已写明"本 fork 停更，去看 mx-llama.cpp"** | iacop README 首两行 |
| 7 | **最强的单条可搬运结论**（跨三源重复出现）：**"每 dot 指令更少 + 不加 barrier + ≤64 VGPR + 4~8 条独立累加链"**；反面：LDS staging 共享激活 −16~−52%、整块加载在 batch>1 −16~−32%、rows 1 −20~−36% | exabit `patches/README.md` 十次构建的结论；KI `latency-hiding.md` DPP 2× |

**给 Strata 的一句话**：三源里"能搬的"仍然是 W835 那三类（A 布局/融合、B wave primitive、C 不可），但本轮新增了 **4 条**此前没进过我们清单的候选（§6.1 的 N1–N4）。

---

## 1 方法与证据等级

| 等级 | 做法 | 覆盖 |
|---|---|---|
| **S** | 下载完整源码树 → `grep -n` 给文件:行 → 读实现 | KI 全树（40.4 MB）、上游全树（39.1 MB）、iacop/fuutott/eslowney 的 gfx906 目录 |
| **P** | GitHub API：PR 元数据 + `pulls/N/files` 补丁正文 | 上游 19 个 PR、5 个 issue |
| **C** | 提交级：`/commits/{sha}` 的 files+patch | 8 个 fork 的 20+ 提交 |
| **R** | 只读到 README/DEVLOG 自述，**未复现代码** | 标 `[自述]` |

本地证据目录：`albus/gfx906_survey/`
- `src/vllm-gfx906-mobydick-gfx906-main/` — KI 全树
- `src/llama.cpp-669204ee.../` — 上游全树
- `fork_iacop/` — iacopPBK 的 13 个 gfx906 文件
- `fork_misc/` — exabit/THEman/JeanP00l 的补丁与 ISA 笔记
- `pr/*.txt` — 8 个上游 PR 的完整补丁
- `_gh.py` / `_raw.py` / `_prfiles.py` / `_cdetail.py` — 复现脚本（token 读 `deploy/tmp/_tok.txt`）

---

## 2 第一部分：KI（`KIntegrated/vllm-gfx906-mobydick`）

### 2.1 谱系与规模（先钉死"这是谁的代码"）

```
nlzy/vllm-gfx906  (原始 gfx906 移植)
  └─ ai-infos/vllm-gfx906-mobydick
       └─ KIntegrated/vllm-gfx906-mobydick   ← 我们说的 KI，24 个 gfx906/* 分支
            FA 内核来自 cassettesgoboom/gfx906-fa-vllm (Copyright Nick)
            ISA 知识来自 skyne98.github.io/wiki-gfx906 (Oleksii Halahan)
```

- 规模：**65 个** `.cu/.cuh/.cpp/.py/.json` 引用 gfx906；**33 个**文件名含 gfx906；`docs/gfx906/` 下 **100+** 篇 DEVLOG/RECON/RELEASE。
- 分支即实验账：`gfx906/{fa-integration, fa-cover-1, int8-packed, e2-packed, c5, dflash2, moe-opt, nh2-int8-gemv, qsa-fn, triton-1, wht1-*}` + 逐版本 `gfx906/v0.24.0rc0.x … v0.32.1`。

### 2.2 Attention：自建 CUSTOM 后端（`vllm/gfx906_fa/` + `csrc/gfx906_fa/`）

| # | 手法 | 代码位置 | 关键实现 | 实测（KI 自述） |
|---|---|---|---|---|
| A1 | **Q8_0 KV 的 tile FlashAttention**，内层用 dp4a | `csrc/gfx906_fa/kernel/fattn-q8.cuh`（1112 行，:9 注释；:429/:504 `static_assert(nbatch_K % 4 == 0, "for sdot4")`） | `int8_t Q_values` + `half Q_scales`；`K_row_padding = 16`（:942-943）——**LDS 行填充** | decode 通道主力 |
| A2 | **gather + quantize 融合成一趟** | `csrc/gfx906_fa/gfx906_fa_gather.cu:9-20` | 原 Python 路径两趟 HBM（`key_cache_q8[block_table]` → permute+contiguous），改为一 workgroup 处理 `(seq, kv_head, token_pos)` | 63.56 t/s 里程碑 |
| A3 | paged KV → Q8 量化 kernel | `gfx906_fa_quant.cu:57`（`quantize_q8_0_dense_kernel`）、`:107`（`reshape_and_cache_q8_kernel`） | | |
| A4 | **B=1 decode 并行：GQA head packing（NC2）+ KV split** | `vllm/gfx906_fa/gfx906_fa_backend.py`、`..._paged.py`；env `GFX906_FA_NC2` / `GFX906_FA_KVSPLIT` | 每 KV 块打包 8 个 Q head；split-combine | 245 → 58.3 µs/layer @Sk=2176（**4.2×**） |
| A5 | **capture 形状**：CG 支持默认 `UNIFORM_SINGLE_TOKEN_DECODE` | `vllm/platforms/rocm.py:497-519` 注册 CUSTOM 为默认后端 | 仅这一项：MoE **22.44 → 52.90 t/s** | |
| A6 | 直接 paged decode（B≥2/Sq≤16） | env `GFX906_FA_DIRECT_PAGED{,_MIN_BATCH,_MAX_SQ}` | 跳过 gather | |
| A7 | BSHD 原生输出，copy pile **7→2** | README §1 | 专用 decode q-pad buffer + 融合 fp16→fp32 cast + 延迟 `cu_seqlens.to(long)` | +0.6~0.7 t/s |
| A8 | kv_split 在 prefill 强制 1（`seq_q>2`）；NC2 fail-closed（只实例化 {1,2,8}） | README §1 | 防越界与无效组合 | |
| A9 | **gather buffer 生命周期**：容量宽度只增 + 每代 capture 标志 | `DEVLOG-fa-attention.md`、`oom-256k-prefill.md` | 修前 60k prefill 点已 7.79 GB / 152 代；修后 250k 通过 | TP=2 131k：22.4 → 40.9 t/s |
| A10 | LEGACY=0（Q8 side buffer）已知会与 warmup/COW 脱同步 ⇒ **默认 LEGACY=1** | README 环境表 | | |

### 2.3 MoE：自建 W4A16 grouped GEMM（这是它最硬的资产）

| # | 手法 | 位置 | 细节 |
|---|---|---|---|
| B1 | **W4A16 MoE grouped GEMM**，fp16 dot2 内层 | `csrc/rocm/moe_q_gemm_gfx906.cu:54` `__ockl_fdot2(dq[i], v.h[i], result, true)` | 修掉上游 modular pipeline 在 gfx906 上的 **3.49 t/s 崩盘**（−71%） |
| B2 | **packed CAS 原子加**做跨 expert 归约 | 同文件 `:58-88`（`atomic_add_pk2_f16` / `pk4`，32/64-bit CAS 循环），`:349`（gemm2 走 pk4） | 避免先落 fp32 再转 |
| B3 | gemm2 lane-column re-tile（512 线程） | `:397`（`__launch_bounds__(THREADS)`）、`:632-636` 注释 | 26.8 → 22.3 µs/call |
| B4 | gemm1 M=1 re-tile（`VLLM_GFX906_MOE_NPT=2`，默认关） | `:665-669` | TP=2 时 +1.23~1.32%，TP=1 中性 |
| B5 | 加载期 repack（AWQ int4 / 128-group，~65 s），兼容 MoeWNA16（N-first uint8）与 AutoAWQ（K-first int32）两种布局 | `vllm/.../fused_moe/experts/gfx906_w4a16_moe.py` + `oracle/int_wna16.py` | |
| B6 | **逐形状 config JSON**（tuning 落盘，不靠启发式） | `vllm/.../fused_moe/configs/E=20,N=1536,device_name=AMD_GFX906,dtype=int4_w4a16.json` 等 6 个 | E=256/N=128..1024、E=128/N=192(int8_w8a16) |
| B7 | M=1 top-k 专用 kernel | `csrc/rocm/moe_topk_gfx906.cu:61`（`__launch_bounds__(64)`） | **bit-equal 且单测更快，但在 CUDA-graph 回放里输** ⇒ 默认关（`VLLM_GFX906_TOPK_M1`） |

### 2.4 Dense：M≤16 的 W16A16 GEMV 家族

| # | 手法 | 位置 | 细节 |
|---|---|---|---|
| C1 | 行并行 GEMV：`RPT` 行/线程、`KCHUNK`∈{512,1024,2048,4096}→64~512 线程、`KSPLIT=K/KCHUNK` | `csrc/rocm/dense_gemv_gfx906.cu:16-18`、`:92-107` | |
| C2 | **fp16 dot2** 内层 | `:88` `__ockl_fdot2` | 8-half 用 4 条 dot2 |
| C3 | packed 2-half 原子加（RPT=2 epilogue） | `:47` `atomic_add_pk2_f16` | K-split 归约 |
| C4 | 长 K n==1 GEMV（K=17408 down_proj，KCHUNK=1024/RPT=2） | README §3 | **227.6 µs = 100% HBM 地板** vs triton_matmul 794 µs |
| C5 | m<4 → padded LLMM1；m==1 → GEMV RPT=1（消除 shared-expert gate 的 `F.pad`） | `vllm/model_executor/layers/utils.py:219-262`（`_llmm1_tiny_m`、`_gfx906_gemv_long_k`）；kill switch `VLLM_GFX906_DENSE_GEMV=0` | −401 µs/step |
| C6 | **W4：M=5..16 skinny rail**（权重行并行 RPT=1、精确 M 模板、grid (N, ksplit)、fp16 atomicAdd K-split epilogue），门控 M≤7 全尺寸 / M=8≤32MB / M≥9≤10MB | `csrc/rocm/skinny_gemms*.cu`；`VLLM_GFX906_SKINNY_M16`（默认关） | N=8 并发 decode：35B **+14.5%**、27B **+6.1%**（30 次 soak） |
| C7 | `waves_per_eu = 1` 作为 triton 默认 | `utils.py:202` 注释"best for gfx906" | |

### 2.5 构建级（不改算法，只改编译）

| # | 手法 | 位置 | 数字 |
|---|---|---|---|
| D1 | **逐文件 `-mllvm -amdgpu-sched-strategy=max-ilp`** | `CMakeLists.txt:1626-1665` | gptq_gemm −15~−26% 时间；FA decode +2~5%；dense serving +7.7%（25.52 vs 23.70） |
| D2 | 该 flag **对 MoE kernel 是负的**（serving −2.2%）⇒ 只给 W4/FA/skinny 的源文件，**不走 `CMAKE_HIP_FLAGS`** | 同上注释 | 这是"一揽子 flag 会骗人"的实证 |
| D3 | q_gemm 按 M 拆文件：M=1 用 max-ilp（+19~24%），M≥2 不用（否则 −14~−23%） | `CMakeLists.txt:440` + `q_gemm_m1_maxilp.cu`；`VLLM_GFX906_QGEMM_M1_MAXILP=0` | |
| D4 | gfx906_fa 扩展**只在 `VLLM_GPU_ARCHES` 命中 gfx906 时编译**，否则给 no-op target（防非 gfx906 构建报 unknown target） | `CMakeLists.txt:1566-1622` | |
| D5 | `HIP_SUPPORTED_ARCHS` 明确含 gfx906 | `CMakeLists.txt:52` | |

### 2.6 其它落地修复（都不是 kernel，但都在收益链上）

| # | 修复 | 位置 |
|---|---|---|
| E1 | GemmaRMSNorm 的 `(1+w)` 分解改为在输入 dtype 里算 `w'=1+w`，才能走融合 RMS-norm kernel | `layernorm.py`（README §4） |
| E2 | GDN `core_attn_out` 零填充在 packed-decode 快路径上删除（`GFX906_GDN_EMPTY_CORE_OUT`，默认开） | 同上 |
| E3 | fastsafetensors GDS 不支持时 catch **裸 `Exception`**（原来只 catch RuntimeError ⇒ 引擎直接死）→ 加载快 2.6× | `model_loader/weight_utils.py` |
| E4 | hipify 同目录 copytree 在 Py3.12 in-source 重建时崩 | `cmake/hipify.py` |
| E5 | 设备名从 GCN arch 推导（torch import 后 amdsmi 返回 0 handle） | `platforms/rocm.py:872` 附近 |
| E6 | bf16 checkpoint 自动降 fp16（gfx906 无 bf16 指令） | `platforms/rocm.py:553-554` |
| E7 | fill/copy 三处 bit-exact launch 删除（+1.15%）；其余归属清楚（gemm zeroing 被 grid.z 原子 K-split 强制、H2D 微拷贝属上游） | README §4 |
| E8 | TP=2 CPU 卡线程：HIP blocking-sync shim（**未根治**，ROCR-Runtime 两处修复未合上游） | `cpu-stuck-threads.md`、`gfx906-blocking-sync.pth` |

### 2.7 可复用的 ISA 事实（KI 转抄 skyne98 实测）

| 事实 | 数字 | 对我们的意思 |
|---|---|---|
| LDS 列式读，`ld=32` vs `ld=33` vec4 | **1865 → 3974 GB/s（2.13×）** | 我们只有 2 处 `+1` pad（W835 §3-1） |
| DPP `row_shr:1` vs LDS+barrier | **~1778-1784 vs ~906 Gxchg/s（≈2×）** | 我们 `__shfl_xor` 193 处/31 文件 |
| bf16 无硬件路径（标量 `v_fmac_f32` upcast） | QSA kernel pair fp16 26.5 ms vs bf16 116.5 ms = **4.40×** | 我们已 `PROMPT_F16=1`，已吃到 |
| `dot4c/dot8c` 不可用，`dot4/dot8/dot2` 可用 | 汇编器 | 别再试折叠形式 |
| int8 KV 在 gfx906 上 prefill **慢 2.5–2.7×**，decode 中性 | KI 实测 | 我们 `--kv k8v4` 是否付了同样代价，**仍未测**（W835 §9.4 挂起） |

### 2.8 KI 的死路清单（负结果，最省钱的部分）

来自 `DEAD-ENDS.md` + `CHANGELOG.md`：

1. **C6 Q8_1 激活量化**：gfx906 无 int8 矩阵硬件，量化 launch 反而净负 ⇒ 否。
2. **K-split v1**（zero_ + 极小 block）：比 LLMM1 慢 **2.4–4.2×** ⇒ 只保留 RPT≥2 单遍。
3. **L1' fp16 M≤4 GEMV**：eager 66.6→53.2 ms，**serving A/B 0.945×** ⇒ "eager 赢 ≠ serving 赢"。
4. **T-1 int8 drafter**：探针 +15~18%，最终 k=4 parity −1%，"earlier +15–18% 是冷启动误读"。
5. **GPU n-gram**：draft-selection mismatch；CPU proposer 更优。
6. **S2 topk M=1**：单测赢，图回放输（见 B7）。
7. **gemm1 re-tile V1/V3/V4**：isolated 赢，TP=1 serving 不迁移。
8. **ALU 换指令（dot2/dot4/dot8 swap）在 gather 型 kernel 上无效**：dp4a 已满速，B=1 decode 是 gather-HBM bound ~2.7× ⇒ 判据必须先做 **ISA rate probe + roofline**，不能凭"换指令更快"。

---

## 3 第二部分：llama.cpp 上游里对 gfx906 生效的代码

### 3.1 架构识别链（决定后面所有分支）

| 位置 | 内容 | 后果 |
|---|---|---|
| `vendors/hip.h:181` | `#define __CUDA_ARCH__ 1300` | HIP 下把所有 `__CUDA_ARCH__ >= x` 判据拉满（所以 ggml-cuda 的"新架构"路径在 AMD 上都会被编译进来，靠后面 `AMD_*_AVAILABLE` 再关） |
| `vendors/hip.h:183-193` | `__gfx900__/__gfx906__/__gfx909__/__gfx90c__` → `GCN5`；`GCN5‖GCN4` → `GCN` | gfx906 的**唯一编译期总开关**是 `GCN` |
| `common.cuh:70-78` | `GGML_CUDA_CC_VEGA20 = 0x1000000+0x906`，注释逐字 **"MI50/Radeon VII, minimum for dp4a"** | 运行期 arch id |
| `common.cuh:98` | `GGML_CUDA_CC_IS_GCN(cc) = (cc > OFFSET_AMD && cc < CDNA1) \|\| IS_GCN_APU` | gfx906 落在 GCN 区间 |
| `common.cuh:46` / `:401-407` | `WARP_SIZE 32`，但 `ggml_cuda_get_physical_warp_size()` 对 `__GFX9__/__GFX8__` 返回 **64** | 软件按 32 lane 分组、物理是 64 ⇒ 所有"半波"问题 |
| 构建 | 必须 `GPU_TARGETS=gfx906`：`gfx9-generic` 目标**排除** `v_dot4_i32_i8`/`v_fmac_f32` | exabit `ISA-NOTES.md` 用 LLVM 指南行号佐证；KI 同样逐字写过这个坑 |

### 3.2 指令级开关

| 位置 | 内容 |
|---|---|
| `common.cuh:722-724` | `ggml_cuda_dp4a()`：`#if defined(CDNA) \|\| defined(RDNA2) \|\| defined(__gfx906__)` → `__builtin_amdgcn_sdot4(a,b,c,false)`（gfx900/gfx906 之外另有 RDNA1 的手写 `v_mul_i32_i24` 路径） |
| `common.cuh:771-788` | `V_DOT2_F32_F16_AVAILABLE` 定义含 `__gfx906__`；`ggml_cuda_mad(float&, half2, half2)` 内联 `v_dot2_f32_f16` |
| `common.cuh:278-293` | `AMD_MFMA_AVAILABLE` 只给 `CDNA`；`AMD_WMMA_*` 只给 `RDNA3/RDNA4` ⇒ **gfx906 两条都没有** |
| `fattn-common.cuh:107,137` | 用 `V_DOT2_F32_F16_AVAILABLE` 决定 KQ 点积写法 |

### 3.3 MMQ（prefill 主力）

| 位置 | 内容 | 备注 |
|---|---|---|
| `mmq-config-gcn.cuh`（**新增文件**） | `ggml_cuda_mmq_get_config_gcn(type, J, fallback)`：按 (type, J, fallback) 返回 `(nthreads, occupancy, I, J, sram_layout, K_vram, stream_k)` | 由 **PR #27841**（merged 2026-08-28，+281/−0）引入；gfx906 的 tile 从"通用表"变成"GCN 表" |
| 典型项 | Q4_0：`I=256, J=8..64`；Q8_0：`I=512, J=8..128, K_vram=128`；Q4_K/Q5_K/Q6_K：`I=256/512, J=8..64, SRAM_LAYOUT_Q8_1/Q6_K`；K-quant 还有 `nthreads=512` 的项 | 表里只有 `J=2` 没有 —— GCN 用 2 字节对齐的 dp4a tile |
| `mmq.cuh:10-13` | `MMQ_ITER_K 256`、`MMQ_NWARPS 8`、`MMQ_DP4A_MAX_BATCH_SIZE 64` | |
| `mmq.cuh:232-300` | host/device 两套 dispatch：`#ifdef GCN → get_config_gcn` | device 侧编译期选择，host 侧按 `GGML_CUDA_CC_IS_GCN(cc)` |
| `mmq.cu:389` | `ggml_cuda_should_use_mmq()` | |
| `mmq.cu:433-441` | **`smpbo < 48 KiB` 直接退回 BLAS** | MI50 LDS 64 KB/CU，够 |
| `mmq.cu:508-520` | `if (cc == CC_VEGA \|\| IS_GCN_APU) return n_experts > 0;` —— 注释说 gfx900/909/90c 无 dp4a；**gfx906 不在其中** ⇒ 走到最后一行 `return (!CC_IS_CDNA(cc)) \|\| ne11 < 64;` = **对 gfx906 恒 true** | 即：**上游在 gfx906 上所有 batch 都走 MMQ**，包括大 batch prefill（这与 KI 的"大 M 用 rocBLAS/自建 GEMM"策略相反） |
| `#30837`（merged 2026-10-19） | `static_assert(I % warp_size == 0)`（1 行） | 防 tile 高不是 64 的倍数 |
| `#21168`（merged 2026-03-30） | q4_0/q4_1 MMQ 用 `ds_read_b128`（+27/−10） | LDS 128-bit 读，对 gfx906 的 LDS 带宽直接有益 |
| `#21698`（**open**） | `load_tiles_q8_0` 的 VRAM→LDS 流水（+13/−3） | 未合 |
| `#29927`（merged） | q1_0 解包用 `__builtin_amdgcn_perm`（+20 in mmq-load-tiles / +20 in vecdotq） | |
| `#29478`（merged） | packed byte sub：`__vsubss4` → `__vsub4`（4 文件 +20/−14） | gfx906 上少一条指令 |

### 3.4 MMVQ（decode 主力）

| 位置 | 内容 |
|---|---|
| `mmvq.cu:99,113` / `:134-135` | `MMVQ_PARAMETERS_GCN`：`#elif defined(GCN) \|\| defined(CDNA) → GCN 参数表` |
| `mmvq.cu:190-…` | `get_mmvq_mmid_max_batch_gcn(type)`：逐类型"MMVQ 比 MMQ 快的最大列数"（IQ 系 4-6、Q4_0/Q4_1 6、Q4_K 5…） |
| `mmvq.cu:442-449` | `get_mmvq_mmid_max_batch_for_device()` device constexpr，`#elif defined(GCN)` |
| `mmvq.cu:449-480` | `calc_nwarps()`：GCN 表 `ncols_dst=1 → 2 warps`；2-4 列按类型 1-2 warps |
| `mmvq.cu:312` | 半波（32 lane）分派（#11519 之后 `selectable warp size`） |
| `#11519`（merged 2025-01-30） | mmv 支持可选 warp size（common.cuh +8 / mmv.cu +24） |

### 3.5 FlashAttention（gfx906 走 vec/tile，永远不走 MMA）

`fattn.cu:650-757` 的选择逻辑（gfx906：`turing_mma_available=0`、`amd_mfma=0`、`amd_wmma=0`、`volta_mma=0` ⇒ 落到最后两段）：

```
if (can_use_vector_kernel) {
    if (K/V 都非量化) { if (Q->ne[1]==1 && !gqa_opt_applies) return VEC; }
    else              { if (Q->ne[1]<=2)                   return VEC; }
}
return TILE;
```

- `can_use_vector_kernel` = `Q->ne[0] <= 256 && ne[0]%64==0 && ne[0]!=192 && K->ne[1]%FATTN_KQ_STRIDE==0`（:664）。
- 也就是说 **gfx906 的 decode 走 `fattn-vec`（fp16 K/V 或量化 K/V），prefill/大 batch 走 `fattn-tile`**；`fattn-tile.cuh` 的 KQ 点积在 gfx906 上编译成 `v_dot2_f32_f16`（§3.2）。
- `#15927`（merged 2025-09-10，+124/−33）：tile FA 的 SRAM 读 8/16 B、AMD FP16 点积前置；作者原话 `v_dot2_f32_f16 ... available everywhere except RDNA 1`。
- `#15884`（merged 2025-09-08，+26/−6）：`v_dot2_f32_f16` 进 FA。
- **`#30344`（open，+14/−2）**：给 GCN 单开 tile 配置表 —— `(64,64,32)→nthreads 256, occ 2, nbatch_fa 64, nbatch_K 32`；`(256,256,16/32)→256,2,64,32/64`，其余回落 `config_amd`。**这是最便宜的一条"上游还没合"的 gfx906 收益**。
- **`#29534`（open，+70/−44）**：GCN 的 Q8 FA 用 **wave64**（`fattn-common.cuh` −10/+10、`fattn-vec.cuh` +60/−34），替代现在"32 lane 子波"写法。

### 3.6 其它对 gfx906 有意义的后端路径

| PR/位置 | 内容 | 状态 |
|---|---|---|
| `#28846` | 无 bf16 硬件的设备回退 F32（`common.cuh` +6、`ggml-cuda.cu` +10） | merged 2026-09-13 |
| `#29442` | bf16/fp16→f32 转换分块（`ggml-cuda.cu` +34/−8） | merged 2026-09-25 |
| `#30325` | 无 WMMA 的 AMD 用 SIMT 隐式 GEMM conv2d | merged 2026-10-11 |
| `#11831` | 把 GCN 从"避免 MMQ"的设备表里删掉（mmq.cu ±1） | merged 2025-02-12 |
| 构建开关 | `GGML_HIP_NO_VMM`、`GGML_CUDA_NO_PEER_COPY`、`GGML_HIP_GRAPHS`、`GGML_CUDA_FA_ALL_QUANTS`；`GGML_HIP_MMQ_MFMA` 对 gfx906 无意义（`AMD_MFMA` 只在 CDNA 定义） | `ggml/src/ggml-hip/CMakeLists.txt` |

### 3.7 上游回归警报（本轮新发现，最该提醒的一条）

**issue #31599（open，2026-11-03）**：`#29948` 改了 MoE 的 grid 顺序，gfx906 上 **prefill 掉 15–50%，decode 不变**；修法（报告人自带）是"除 GCN 外保留新序"。数据（同一台 MI60）：

| 模型 | 测试 | master | 回退 grid order | 差 |
|---|---|---:|---:|---:|
| OLMoE-1B-7B Q4_K_M | pp512 | 2300 | 4008 | **+75%** |
| OLMoE | pp4096 | 3837 | 4531 | +18% |
| gemma-4-26B-A4B | pp512 | 557 | 1118 | **+100%** |
| gpt-oss-20b | pp512 | 896 | 1516 | +69% |
| Qwen3.6-35B-A3B UD-Q5_K_XL | pp4096 | 1040 | 1499 | +44% |

机制（他的 rocprofv3）：L2 命中变好、RAM 读变少，但**CU 之间工作量失衡**——平均每 CU 相同，最忙 CU 是平均的 4×，有些 CU 完全空。dense 不受影响。

⇒ 对 Strata：我们不是 ggml，但"**gfx906 的 grid/CTA 顺序会导致 CU 饥饿**"是一条可直接在我们的 `native_router` / `iq_kernels`（grid.z 分专家）上复测的假设，判据是每 CU 的 `SQ_INSTS` 方差 + 最忙/平均比。

### 3.8 上游 gfx906 相关 PR 台账（66 条里筛出 19 条有实质代码的）

| PR | 标题（缩写） | 状态 | 日期 | 改动 |
|---|---|---|---|---|
| 27841 | hip: add missing AMD GCN MMQ config | **merged** | 2026-08-28 | 新建 `mmq-config-gcn.cuh` +281 |
| 30837 | DP4A MMQ tile height multiple of warp size | **merged** | 2026-10-19 | +1 |
| 29927 | amdgcn_perm for q1_0 unpacking | **merged** | 2026-10-03 | +40 |
| 29478 | `__vsubss4` → `__vsub4` | **merged** | 2026-09-26 | +20/−14 |
| 21168 | ds_read_b128 for q4_0/q4_1 MMQ | **merged** | 2026-03-30 | +27/−10 |
| 15927 | larger SRAM reads (tile FA) + AMD FP16 dot | **merged** | 2025-09-10 | +124/−33 |
| 15884 | v_dot2_f32_f16 for FA | **merged** | 2025-09-08 | +26/−6 |
| 11831 | remove GCN from MMQ-avoid list | **merged** | 2025-02-12 | +1/−1 |
| 11519 | selectable warp size in mmv | **merged** | 2025-01-30 | +34/−14 |
| 11244 | parse arch from gcnArchName | **merged** | 2025-01-14 | +75/−12 |
| 30325 | SIMT conv2d without WMMA | **merged** | 2026-10-11 | +2/−2 |
| 28846 | F32 fallback without BF16 hw | **merged** | 2026-09-13 | +16/−2 |
| 29442 | BF16/FP16→f32 chunking | **merged** | 2026-09-25 | +34/−8 |
| **30344** | **fattn tile GCN tune config** | **open** | 2026-10-11 | +14/−2 |
| **29534** | **wave64 for GCN Q8 FA** | **open** | 2026-09-27 | +70/−44 |
| 21698 | better VRAM→LDS pipeline in load_tiles_q8_0 | **open** | 2026-04-09 | +13/−3 |
| 16291 | bpermute → swizzle (gfx906, +20% avg) | closed 未合 | 2025-09-27 | +658/−567（含脚本） |
| 26466 | `__shfl_xor_sync` → DPP | closed 未合 | 2026-08-02 | +121/−58（10 文件） |
| 29910 | fix VGPR spills on Q2_K | closed 未合 | 2026-10-03 | +3/−10 |
| 30348 | CI: spill check every AMD arch | open | 2026-10-11 | CI |

---

## 4 第三部分：llama.cpp 的 gfx906 专属 fork

### 4.1 谱系（先把"谁是谁的分支"钉死）

```
ggml-org/llama.cpp
 └─ iacopPBK/llama.cpp-gfx906        150★  b7924  "本 fork 停更 → mxxm-t/mx-llama.cpp"
     ├─ fuutott/llama.cpp-gfx906      2★   v6  Q8 FA + DPP（2025-11）
     └─ eslowney/llama.cpp-gfx906     8★   D=128 / gemm autotuner / asm（2025-09）

独立线：
 exabit-io/llama.cpp-gfx906-tuning  → exabit-io/mx-llama.cpp（4×Vega20 生产，补丁 0001-0009）
 marcelromano/lcpp-mi50-3090        → wave64 MMVQ / GQA-shared FA / wave64 GDN（AI 辅助，自述）
 sixvolts/llamacpp-gfx906-furnace   → QSA 长上下文 + per-type repack + KV 窗口（2026-11）
 milpster/gfx906-llama-cpp          → 200k 长文 + mlock staging + ngcache（2026-09）
 THEman6989/llama.cpp-gfx906-wrapper→ "turbo" 一体化 patch（wave64 + TurboQuant KV）
 JeanP00l/mi50-qwen3.8-fast         → 3 个精确 patch 脚本
 mixa3607/ML-gfx906  376★           → 构建仓（含 gfx906 patch），非内核仓
只做构建/容器：xxDoman/llama-mi50-rocm7.2、anng-phtk/rocm-vega-llama.cpp、knguyen298/llama-swap-gfx906
```

### 4.2 `iacopPBK/llama.cpp-gfx906`（事实上的"基线 fork"，32 个 gfx906 文件）

目录 `ggml/src/ggml-cuda/gfx906/`（S 级，已逐文件读）：

| 文件 | 行/字节 | 内容 | 备注 |
|---|---|---|---|
| `gfx906-config.h` | 878 B | `GFX906_MMQ_NWARPS 2`；`GFX906_KVQ_MOE_CACHE_ENABLED 0`（Q8 缓存**默认关**）；`GFX906_Q8_CACHE_TOTAL_SIZE 128MB`；`GFX906_ROPE_ENABLED 1` | 开关集中地 |
| `gfx906-common.cuh` | 10.9 KB | ① `sgpr_broadcast_*`（`__builtin_amdgcn_readfirstlane`）；② `v_exp_f32`/`v_log_f32`/`v_rcp_f32` 快数学；③ **融合 DPP 归约**：`v_add_f32_dpp`/`v_max_f32_dpp` 的 xor1/xor2/xor8 宏；④ `hip_shuffle_xor4/16`（xor4 用两条 `v_mov_b32_dpp` row_shl/shr 拼，xor16 用 `ds_swizzle_b32 SWAP,16`）；⑤ `gfx906_shfl_xor_sync` 统一派发；⑥ 8 线程专化归约（Q8_1 量化用） | **对我们 `qsa_decode_attn.cu:478` 那条 DPP 的正规化版本** |
| `attention/fattn-q8.cuh` | **1003 行** | Q8_0 KV 的 tile FA；`GGML_CUDA_FATTN_TILE_CONFIG_CASE` 逐 head-dim 配置（40/64/.../576×512）；`v_dot4_i32_i8` 内层 | 与 KI 的 `fattn-q8.cuh` 同源（都来自 gfx906-fa-vllm 谱系） |
| `attention/rope.cuh` | 163 行 | `__sincosf` 合并 sincos + yarn 参数化 | |
| `fused/graph-fusion.cuh` | 267 行 | 图级模式识别 **RMS_NORM → MUL → MUL_MAT**，把 norm 融合输出 Q8_1 直接喂 MMQ；决策按 graph 缓存（避免 O(n²) 扫描） | 默认关（`GFX906_KVQ_MOE_CACHE_ENABLED 0`） |
| `fused/norm-fused-q8.cuh/.cu` | 19 行头 | `ggml_cuda_op_rms_norm_fused_q8_1()` + `ggml_cuda_get_q8_1_buffer_size()` | |
| `fused/mmq-prequantized.cuh` | 93 行 | `mmq_switch_type_prequantized()`：接受**已经量化好的 Q8_1** 直接进 17 种 mul_mat_q_case | 省掉 quantize launch |
| `fused/gather-q8.cuh` | 16 行 | `gather_q8_1_rows_cuda()`：按 ids 从 Q8_1 张量取行（MoE cache） | |
| `matmul/mmq.cuh` | 93 行 | `gfx906_load_q4_0/q4_1_quants_vectorized()`：**2×`int4` 代替 8×标量**（128-bit load） | 对应我们"dword 对齐/宽读"候选 |
| `matmul/mmq-prefetch.cuh` | 231 行 | `gfx906_prefetch_y_tile_v4()`：下一轮 y-tile 的 `global_load_dword` 预取，藏延迟 | |
| `matmul/mmf.cuh` | 176 行 | `gfx906_mul_mat_f16_packed`：M 9–2048 的 fp16 GEMM，tile 32×64×64，`__launch_bounds__(256,4)` | 补 9-2048 的空白（rocBLAS 与 GEMV 之间） |
| `matmul/mmvq-q4_0/q4_1/q8_0.cuh` | — | warp 协作的 MMVQ | 2026-01 批次 |
| `quantize/epilogue.cuh` | — | DPP-based Q8_1 epilogue | |
| `quantize/q8-cache.cuh` | 650 行（改动） | 跨 op 的 Q8 缓存（**默认关**，refactor WIP） | |
| `attention/instances/*` | 8 个 | head dim 40/64/80/96/112/128/256/576×512 的模板实例 | |

README 的批次说明（S 级可查）：
- **2511**：DPP 归约 + `fattn-common.cuh` GCN 线程数/tile + `fattn.cu` Q8 tile 选择 + `mmq.cu` Q4_0/Q4_1 向量化 load。
- **2512**：Q8_0 MMQ 软件流水 + `need_check` 路径避 LDS 冲突 + MXFP4 流水 + **MoE sub-warp shuffle 的 wave64 修复**（修 gpt-oss 载入问题）。
- **2601**：Q4_0/Q4_1/Q8_0 三个 warp 协作 MMVQ + **MoE 小矩阵的 32 线程半波分派**。
- **2602**：Q8 缓存重构（仍关）+ flags 修正 + 输出正确性修复。

### 4.3 `fuutott/llama.cpp-gfx906`（v6，16 个 gfx906 文件）

单提交 `89315ff0` "Advanced GFX906 optimizations with Q8 flash attention and DPP reductions"：
- `gfx906/gfx906-fattn-q8.cuh` **1079 行**（比 iacop 的大，多了 GQA/多实例）
- `gfx906/gfx906-mmq.cuh` 80 行（MMQ 侧的组合式改动）
- `gfx906/gfx906-common.cuh` 228 行 / `gfx906-config.h` 58 行
- 改 `common.cuh` +46/−10、`fattn-common.cuh` +16/−2、`fattn.cu` +62/−1、`mmq.cu` +10、`mmq.cuh` +25/−2、`ggml-hip/CMakeLists.txt` +11
- 附 `SCRIPT_overclock_upp_MI50.sh`（92 行，**改 UPP/功耗上限**）与两张 power-sweep 图

### 4.4 `eslowney/llama.cpp-gfx906`（23 个文件，D=128 专线）

`6144f46f` 一次提交塞进整套：`fattn-tile-f16-gfx906.cu`（432 行）、`gemm-gfx906-autotuner.cuh`（422）、`gemm-gfx906.cuh`（538）、`gemm_gfx906_double_buffer.cuh`（279）、`gfx906-wave-primitives.cuh`（436）、`gfx906-wave-primitives-swizzle.cuh`（82）、`gfx906-memory-isa.cuh`（404）、`gfx906-memory-patterns.cuh`（284）、`gfx906-asm-kernels.s`（187 行手写汇编）+ wrapper（195）、`gfx906-init.cu`（327）、`gfx906-memcpy.cuh`（99）+ `.hsaco`。
**质量警告**：同一提交把 metal/vulkan/cann/cpu 等无关后端也大改（README −523 行等），明显是**旧树整体回灌**，不宜整包采信；但 `wave-primitives` / `memory-patterns` / `gemm-autotuner` 三个头文件是可读的手法来源。

### 4.5 `exabit-io`（4×Vega20 生产线；补丁级，最接近"可审计"）

**11 个补丁**（`patches/0001-0009` + 两个 MMVQ 补丁），逐条都有实测：

| 补丁 | 内容 | 实测 |
|---|---|---|
| mmvq-max-batch-16 | `MMVQ_MAX_BATCH_SIZE` 8→16 + 模板实例化 | 4 卡 batch 9/12/16：96.5→162.6 / 122.5→174.6 / 152.5→170.7 tok/s；**单卡变差**（113 VGPR，2 waves/SIMD） |
| mmvq-gfx906-knobs-and-q8-fastpath | Q8_0 快路径（每行权重块只读一次、每列激活块只读一次、两个 scale 合成一次乘）+ gfx906 launch 表 **rows 4/warps 1（≤8 列）、rows 2/warps 1（>8 列）** | 上游 b10288：tp4 b8 +8% / b12 **+62%** / b16 +36%；单卡 b4 +14% / b8 +37%；`test-backend-ops` 1186/1186 过，PPL 不变 |
| gfx906 MMQ tile 表（`mmq-config-gfx906.cuh`） | 逐类型 tile + 14 行 K-quant 补丁 | prefill Q8_0 **+33%**（848→1130 tok/s 四卡；234→315 单卡）、Q6_K +26%、Q4_K_M +7%；decode +4% |
| 0001 | 融合 RMS_NORM+MUL 同时输出 Q8_1 到缓存 | 去掉 128 次 quantize launch；exact；**0%**（融合成本=norm+quant 成本） |
| 0002 | 融合 norm 内做残差 ADD | 129 launches；exact；**+1.6%** 单流 |
| 0003 | GDN 生产者折叠（q/k L2 norm、beta sigmoid）进 GDN kernel | 144 launches；**+1.8%**；0009 后 bit-exact |
| 0004/0008 | 1 列 MMVQ 旋钮（rows/nwarps/vdr8） | 整块 vdr8 在 1 列：**+2.8%**（split）/ **+7.1%**（单卡） |
| 0005 | `GGML_TP_AR_MAX_NE`：peer-write allreduce 的显式尺寸门 | `=20481`：单流 **+14.5%**，2 流 +19%，8+ 不变 |
| 0006 | add+norm / GDN 折叠只对 ≤64 行生效 | 修 0003 的 **−7% prefill** |
| 0007 | GDN 折叠 bitmask + `GGML_CUDA_GRAPH_OPT=2` 多流图优化 | 图优化：两种摆放都是 0 |
| 0009 | q/k L2 折叠用独立 kernel 的求和顺序 | wave64、S_v=128 时 bit-exact |

**被证伪的变体（十次构建的结论，最值钱）**：rows 1 任意 warp −20~−36%；rows 2/warps 2 −14~−17%；rows 8 寄存器压力；整块 32 权重/线程 −16~−32%（只在 batch 1 +5%）；LDS staging 共享激活 −16~−52%（barrier）；对齐 dword 载入 −9~−17%；`GGML_CUDA_FORCE_CUBLAS` 做 prefill 打平（退役）。
经验法则逐字：**"fewer instructions per dot product wins; anything that adds a barrier or lengthens a dependent chain loses; registers beyond about 64 per thread lose."**

### 4.6 `marcelromano/lcpp-mi50-3090`（wave64 内核线，AI 辅助，**未复现**）

| 提交 | 内容 | 规模 |
|---|---|---|
| `c4d0a5911` | **gfx906 MMVQ**：lane-packed rows + DPP 归约 + sub-4-bit i-quant dot；`GGML_EXP_MMVQ_GCN2*` 开关 | `mmvq.cu` **+1173**、`vecdotq.cuh` +671、`mmq-config-gcn.cuh` +295、`mmq-vec-dot.cuh` +55、`mmvf.cu` +30、`vendors/hip.h` +25 |
| `2a26d6e1` | **GQA-shared FA decode**：一个 block 服务一个 KV head 的所有 Q head（K/V 只读一次），q8_0/q4_0 K/V、head 256、1-8 token；`GGML_EXP_FA_LC` | 新文件 `fattn-vec-lc.cuh` 618 行 |
| `6f41f8bc` | tensor-core chunked GDN（对 gfx906 无用）+ **wave64 decode kernel** + per-sequence recurrent cell 映射 | `gated_delta_net.cu` +294/−10 |
| `60043155` | 双卡 tensor split 的 **BF16 wire AllReduce**（F32 保持，partial 打包 BF16 过 host，PCIe 流量减半） | `allreduce.cu` +203/−25 |

自述：2×MI50、Qwen3.8-27B、layer-split、8k ⇒ 29.9 tok/s vs 社区 gfx906 构建 18.0；**明确写"AI 工具参与实现，未做隔离测"**（issue #31765/#31770 原文）。

### 4.7 `sixvolts/llamacpp-gfx906-furnace`（QSA 长上下文线，2026-11，活跃）

不是"新 kernel"，而是**模型/图/缓存层**对 gfx906 的形状优化（分支 `gfx906-perf`）：
- `qsa: one block-key cache tensor per layer over all streams`（4f30c1bd）——每层一个 blk-key 缓存、所有 stream 共用，**每个 ubatch 同一张图**
- `qsa: block-key cache per stream`（044c183b）
- `qwen4exp: QSA keeps top_k/r whole blocks plus the tail, as the reference does`（657b8f78）
- `cuda: repack switch helper, 逐类型 K-quant 开关`（0c63b696）
- `kv-cache: LLAMA_KV_SEQ_HEADROOM`（db919bab / e8ea0d74）——新序列按 headroom 间距而不是池比例
- `MMQ: pad the q8_1 activations and ids_dst for a full tile`（f310d364，跟随上游 fc9ce6b9d）
- `speculative: MTP catch-up 在下一次 target decode 里做`（21be4348/0e13070c）

### 4.8 `milpster/gfx906-llama-cpp`（200k 长文 + 主机侧线，2026-09）

- `cuda: gfx906 packed-byte subtraction (upstream #29478)`（1373e889）——**把上游补丁单独落到自己的树**
- `loader: LLAMA_MLOCK_POPULATE staged pread+mlock`（7d30edc5）+ `pace staged mlock population` + `lock split host buffers by allocation` —— 专家常驻主机内存的分批锁定
- `sched: env-gated split input copy trace`（954c8aa1）
- `qsa: env-gated indexed sparse flash attention, 200k ctx at ub5696`（c12783c4）
- `server: prompt message deduplication (opt-in)`、`ngram-cache strict gate, p_min, file-backed dynamic cache`
- 自称 `journal/LEDGER-gfx906-rig.md` 记账，**无 gfx906 专属 .cu/.cuh**（S 级：全树只有 2 个文件名含 gfx906，均为文档）

### 4.9 其余（构建/包装类，无内核 patch）

| 仓库 | 性质 | 值得抄的 |
|---|---|---|
| `THEman6989/llama.cpp-gfx906-wrapper` | 单文件 `turbo-gfx906-mtp.patch`（1.46 MB）打到指定上游 commit | 声明含：**wave64 kernels**、**TurboQuant 2/3/4-bit KV（省 78% ctx VRAM）**、**FP16 shadow cache**（绕 ROCm 6.0+ FA 反量化不稳）、**FWHT O(d log d) 旋转**（`GGML_OP_TURBO_WHT`）、`GGML_HIP_GRAPHS=ON`。构建串：`GGML_HIP_GFX906=ON GGML_HIP_GRAPHS=ON GGML_HIP_MMQ_MFMA=ON GGML_HIP_NO_VMM=ON` |
| `JeanP00l/mi50-qwen3.8-fast` | 3 个 python 补丁脚本 | `gfx906-mmvq-q4_0-multicol.py`（Q4_0 多列）、`gfx906-mmvf-few-rows.py`（fp16 少行）、`gfx906-gdn-multicolumn.py`（GDN 多列）；自述 19→48 tok/s |
| `mixa3607/ML-gfx906` | 376★ 构建仓 | "minimal gfx906 patch" + 逐版本 pin；是**二进制/镜像**入口，不是源码资产 |
| `xxDoman/llama-mi50-rocm7.2` | Dockerfile + build.sh + 文档 | "14 个 CPU backend 变体"、patched gfx906 rocBLAS，无内核源码 |
| `anng-phtk/rocm-vega-llama.cpp` | 构建/混合 gfx900+gfx906 | 复现脚本价值 |
| `knguyen298/llama-swap-gfx906` | 容器 | 无 |

### 4.10 跨 fork 手法矩阵（去重后 14 族）

| 手法 | 出现在 | 有实测 | 我们对应 |
|---|---|---|---|
| DPP 归约替代 bpermute/shfl | iacop(common 全) / fuutott / exabit(dpp-warp-reductions.diff) / 上游 #26466(未合) / #16291(未合) | iacop 无；exabit 有 diff 无数字；W835 引 +20% | `qsa_decode_attn:478` 已有 1 处；`native_router` 3 处待改 |
| Q8_0 KV tile FA（dp4a 内层） | iacop 1003 行 / fuutott 1079 行 / KI 1112 行 | KI 有（decode 主力） | 我们 `kv_q8.cu` 已有 |
| MMQ 的 gfx906 tile 表 | iacop matmul / exabit `mmq-config-gfx906.cuh` / marcelromano +295 / **上游 #27841** | exabit +33% prefill | 我们走自研 MMQ，不直接适用；但"逐形状表"方法论适用（我们已有 rocBLAS 表） |
| MMVQ 16 列 / Q8 快路径 | exabit 两个补丁 / marcelromano c4d0a5911 | exabit +62%@b12 | 我们 `native_mmvq.cu` 可对照 |
| norm+add+Q8_1 融合 | iacop fused/*（默认关）/ exabit 0001+0002 | exabit +1.6%；融合本身 0% | HC_Q8 路径有两趟 launch 可省 |
| GDN producer 折叠 | exabit 0003/0009/0012 / JeanP00l gdn-multicolumn | +1.8%，bit-exact | `fused_gdn.cu` 同一类 |
| 图级融合（Q8 缓存） | iacop graph-fusion.cuh（默认关） | 无 | 无对应（我们是静态图） |
| 向量化 128-bit load | iacop matmul/mmq.cuh / exabit 反例（对齐 dword −9~−17%） | 一正一负 | 需按 kernel 实测，不可一概而论 |
| GQA-shared FA decode | marcelromano 618 行 / KI NC2 | KI 4.2× | 我们 `qsa_decode_attn` 的 lane-cell 思路已接近 |
| wave64 GDN / wave64 MMVQ | marcelromano / 上游 #29534(open) | 自述 | `fused_gr.cu` 硬拒 64-lane |
| TurboQuant KV（2/3/4-bit + FWHT） | THEman | 自述省 78% VRAM | 无（我们 k8v4） |
| 长上下文 QSA blk cache / sparse FA | sixvolts / milpster | 自述 200k | 我们有 qsa_select |
| 主机侧 staging / mlock | milpster / 上游 #3779 族 | 自述 | 我们 `--pcie-frac` 与 park 机制 |
| 构建 flags（NO_VMM/NO_PEER/GRAPHS/FA_ALL_QUANTS） | 全部 | 部分 | 我们 build.ninja 已逐字抄 |

---

## 5 三源交叉：出现 ≥2 次即高置信

| 结论 | KI | 上游 | fork |
|---|---|---|---|
| gfx906 有 dp4a、无 MFMA/WMMA | ✅ dequant-instructions.md | ✅ common.cuh:722/278 | ✅ 全部 |
| wave = 64，软件按 32 分组会浪费半波 | ✅ | ✅ `physical_warp_size()` | ✅ iacop/exabit/marcelromano |
| LDS 列式读需 +1 行填充（2.13×） | ✅ lds-layout.md | 间接（MMQ tile 表按 bank 选形） | ✅ eslowney memory-patterns |
| DPP 优于 LDS 交换（≈2×） | ✅ latency-hiding.md | ⚠️ 两个 PR 都没合 | ✅ iacop/fuutott |
| bf16 在 gfx906 上是灾难（4.40×） | ✅ RECON | ✅ #28846 回退 F32 | ✅ 各 fork 都用 fp16 |
| MMQ tile 表要按 gfx906 单开 | ✅ 自建 MoE GEMM | ✅ #27841 新建 GCN 表 | ✅ exabit +33% |
| int8 KV 只买容量，prefill 变慢 | ✅ 2.5–2.7× | — | ✅ exabit（4-bit V 缓存 −18% decode@32K） |
| CUDA 图回放会推翻 eager 结论 | ✅ L1'/S2 gemm1 | — | ✅ exabit 0007（图优化 = 0） |
| grid 顺序影响 gfx906 CU 均衡 | — | ✅ #31599（−15~50%） | — |

---

## 6 对 Strata 的可搬运清单（在 W835 之上更新）

### 6.1 新增候选（本轮才进清单）

| # | 候选 | 来源 | 为什么现在才看见 | 判据 |
|---|---|---|---|---|
| **N1** | **grid/CTA 顺序 → CU 负载均衡**：把按专家/按 tile 的 grid.z 顺序换成"交错"或旧序，测每 CU 的 `SQ_INSTS` 方差与最忙/平均比 | 上游 #31599（rocprofv3 实测 4× 失衡） | 我们从没在 gfx906 上查过 CU 分布，只看总时间 | 同一 run 内 n≥5，比较 `ms/step` + 忙闲比；2×CV |
| **N2** | **单列 MMVQ 的"整块 vdr8 加载"**：一列时一次读整 32-权重块 | exabit 0008（+2.8% split / +7.1% 单卡） | 我们的 decode 就是单列 | A/B，注意"batch>1 时 −16~−32%"的反面 |
| **N3** | **norm(+MUL) 融合输出 Q8_1 直喂量化 GEMV**：省掉 quantize launch，且不吃精度（exact） | iacop `mmq-prequantized` / exabit 0001+0002（+1.6% 来自 ADD 融合，norm 本身 0%） | 我们 `HC_Q8=1` 已量化，但 norm→quant 仍是两趟 | 先数 launch（`STRATA_MMQ_DEBUG_J` 那套不可用，改用 nsys/rocprof 计数），再 A/B |
| **N4** | **逐文件编译 flag**（max-ilp）：同一 flag 对 GEMM 正、对 MoE kernel 负 | KI CMake:1626-1665（−15~−26% vs −2.2%） | 我们 build.ninja 是全局 flags；W765 只验过"漏 DNDEBUG 掉 47%" | 单文件加 flag，编译产物 md5 变、行为不变，再 A/B |

### 6.2 旧候选的现状（W835 §3 七项 + §9 修正）

- **LDS +1 padding**：仍只有 2 处（`dflash2.cu:107`、`qsa_select.cu:1157/1262`）；KI 侧 `K_row_padding=16` 是 LDS 行填充的第三方确认（§2.2 A1）。
- **DPP 归约**：iacop 给了完整实现（xor1/2/8 用 `v_*_f32_dpp`，xor4 用两条 `row_shl/shr` 拼，xor16 用 `ds_swizzle`），比我们 `qsa_decode_attn:478` 的单点写法更系统 ⇒ 可直接照抄到 `native_router`。
- **fp16 dot2**：KI/iacop 都证实其价值；但 W835 §9.2 的"gather 型 kernel ALU 已满速"仍成立 ⇒ **先 roofline 再改**。
- **wave64**：`fused_gr.cu:3101` 硬拒仍未解；上游 #29534 与 marcelromano 给了两个独立实现可参考。
- **Q8 KV FA / rocBLAS 表**：已具备，不动。

### 6.3 不可搬运（硬件，双证）

MFMA/WMMA/tensor-core 路径（`qsa_select` 的 wmma scorer、`GDN_TC`、`PF_FUSED_F16`）；`dot4c/dot8c`；bf16 直算；`GGML_CUDA_FORCE_CUBLAS`（打平）。

---

## 7 未决 / 下一步

1. **N1 先做**（最便宜、且可能是唯一"系统性"收益）：借 #31599 的方法在 Strata 上量每 CU 负载。
2. **N2 单列 vdr8**：一次 A/B（decode 单流）。
3. **roofline 三连**（W835 §9.7 第 0 步仍未做）：`fused_gdn` / `native_qsa_score` / `native_router` 的 ISA rate probe。
4. **int8 KV 的 prefill 代价**（`--kv k8v4`）仍未测 —— 三源里 KI 与 exabit 都报"只买容量、prefill 变慢"，我们可能一直在付。
5. `#30344`（fattn tile GCN 表）与 `#29534`（wave64 Q8 FA）若上游合并，是**唯一不用自己维护的 gfx906 收益**，值得跟踪。

---

## 8 证据索引

| 结论 | 出处 |
|---|---|
| 上游 gfx906 字面 5 处 | `grep -rn gfx906 src/llama.cpp-669204ee.../` |
| dp4a / dot2 宏 | `ggml/src/ggml-cuda/common.cuh:722-724`、`:771-788` |
| GCN5/GCN | `vendors/hip.h:181-193` |
| CC_VEGA20 | `common.cuh:70-78`、`:98` |
| GCN MMQ 表 | `mmq-config-gcn.cuh`（PR #27841） |
| MMQ 恒真判据 | `mmq.cu:508-514` |
| FA 选择 | `fattn.cu:650-757` |
| MMVQ GCN 参数 | `mmvq.cu:190-…`、`:442-480` |
| KI attention | `csrc/gfx906_fa/kernel/fattn-q8.cuh:9/429/504/942-943`、`gfx906_fa_gather.cu:9-20` |
| KI MoE | `csrc/rocm/moe_q_gemm_gfx906.cu:54/58-88/349` |
| KI GEMV | `csrc/rocm/dense_gemv_gfx906.cu:16-18/47/88/92-107` |
| KI 构建 | `CMakeLists.txt:1626-1665`、`:440` |
| KI 数字 | `docs/gfx906/README.md`、`CHANGELOG.md`、`DEAD-ENDS.md` |
| KI ISA 事实 | `docs/gfx906/{lds-layout,latency-hiding,dequant-instructions}.md` |
| fork 文件 | `albus/gfx906_survey/fork_iacop/*`、`fork_misc/*` |
| 上游 PR 补丁 | `albus/gfx906_survey/pr/*.txt` |
| exabit 补丁清单 | `albus/gfx906_survey/fork_misc/exabit_patches_README.md`（原 `patches/README.md`） |

---

## 9 补遗（2026-11-07 05:1x）：上一版漏掉的 12 个仓库

上一版只扫了"KI / 上游 llama.cpp / llama.cpp fork"，**漏掉 Strata 自己的 gfx906 生态**。补齐如下（S 级：看过文件树或文件内容）：

### 9.1 Strata 系（9）

| 仓库 | 内容 | 价值 |
|---|---|---|
| `NightPoetry/strata-gfx906-overlay` | **port overlay**：`diffs/CMakeLists-gfx906.diff`、`overlay/include/strata/hip_compat/*`（`cuMem*`→`hipMem*`、cublas 映射）、`docs/PORT-NOTES-gfx906.md`、`PERF.md` | 16G MI50 跑 rich server 的完整配方；`--stage-ahead 2048` / `--prompt-batch 1536` 的 prefill 阶梯 704→736→815 tok/s |
| `3chet/strata-gfx906-fieldnotes` | 2×Radeon Pro VII 台账，**17 条负面**（lookup-chain / suffix-draft / mtp-q4 / pool-workers / prefill chunk / batch / rocBLAS 表 / kv-grow / calibrate / kv-resident / pool-spin…） | 避免重做；其中 rocBLAS"default 行是判决不是空白"与我们 W830 直接对冲，需核对 |
| `QPhuGit/Strata-gfx906-Argon` | 全树 + `include/strata/kernels/gfx906_dlops.hpp`（sdot4/udot4/dot2 封装）+ `bench/results/2026-10-08-gfx906-qsa-query-swizzle/` | **swizzle 正式实测**：component +14.65%、整模型 prompt +1.19%、token 全同；`q(d)=d XOR ((d>>3)&4)` 自逆 |
| `freapsy/strata-mi50` | 同源全树（`mi50-gfx906`），自述 115 tok/s | 配置对照 |
| `milpster/strata-dflash2-gfx906-mixed-rocm-cuda` | 全树 + `docs/work/rocblas-gfx906-workaround.patch` + rocBLAS 崩溃报告 | **风险输入**：缺 tuned 且缺 fallback 的 GEMM 形状会 SIGSEGV |
| `xxDoman/strata-gfx906` | 0.1.43–0.1.48 逐引擎笔记 + community benchmark | 版本回归旁证 |
| `MarcoTool/PDHyperMix-Strata-gfx906` | prefill/decode 分离 | 架构参考 |
| `Auirsword/z100l-strata` | 海光 Z100L（gfx906）单卡 + DTK 补丁 | 暂不适用 |
| `mixa3607/ML-gfx906` | 376★ 构建仓（含 Strata/llama.cpp） | 构建入口 |

### 9.2 llama.cpp 系（12）

`incode0-debug/llama-cpp-gfx906-multibackend`（CUDA+HIP+Vulkan 单二进制）、`Kausik-A/gemma4-mi50-optimizations`（Q8_1 复用 + fused QKV）、`Luskendeilder/llama.cpp-gfx906-solve-tri`、`mt4wss/llama.cpp-gfx906-solve-tri-fix`、`taobaoww2010-alt/llama-cpp-to-amd-mi50`、`taobaoww2010-alt/llama-cpp-rocm-gfx906`、`dc740/gfx906`（memory-bound FA kernel）、`0FL01/gfx906-qwen3.8fn`、`DByte308/ornith-mtp-gfx906`、`phantomic12/ML-gfx906`、`bowmanjd/franken-llama`（nix）、`logicalor/llama.cpp_rocm_mi50`；`marki-nishicono/prism-llama-prod` 与 `strata-console-prod` 为 **0 字节空仓**。

### 9.3 仍未覆盖（明确列出，不假装穷举）

- 非 GitHub：`skyne98.github.io/wiki-gfx906`（唯一已用的站外源）、Docker Hub `unverbraucht/vllm-gfx906`、HF 模型卡/讨论区、Reddit/Discord。
- 私有与已删：上述两个空仓、`taobaoww2010-alt` 的二进制附件。
