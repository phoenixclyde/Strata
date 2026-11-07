# W737 routeK -> Strata：可移植面清点与候选清单（源码级修订版）

> 触发：机主问「结合我们 ki(routeK) 的项目，strata 还有提升的空间吗？可以做一些算法移植」，随后追问
> **「你为什么不去 ki 的库看呢？166 也有完整源码」**。
> **本版为修订版**：初版（`W737_ROUTEK_PORT.md.bak_v1`，23,953 B / md5 `2334de36b17a`）的 routeK 侧证据
> **取自归档件 `ARCHIVE.md`**，不是 routeK 自己的源码树。机主指出后已按项目铁律重做
> （铁律：*读到文档说「已修/已有/默认开」，必须去运行期树 grep 那个标志物再下结论*）。
> **本版 routeK 侧证据一律来自 `166:/home/albus/routeK/src` 与 `/home/albus/routeK/*.md` 的逐行实读。**
> 基线：Strata **0.1.41**（本机 `deploy/tmp/src411/Strata-0.1.41`，2,422 文件）。
> 证据等级：**[routeK源码]** / **[Strata源码]** / **[routeK实测]** / **[文档]** / **[推测]**。
> **本轮只读**：未发车、未改参数、未动生产；166 上只读文件。

---

## §0 结论速览

1. **代码不能搬 -- 现在是源码确证，不是推断。** routeK 树 = vLLM fork（Python + torch + `csrc/`）；
   Strata 树 = 独立 C++/HIP 引擎。**routeK 树里同名内核计数 = 0**：
   `fused_gr` 0 / `s2_expert_grouped` 0 / `native_mmvq` 0 / `iq_kernels` 0。**[routeK源码]**
2. **两边同一台机器、同一张卡。** routeK 测试台 = `albus@192.168.50.166`（`ARCHIVE.md` §2.3）；
   我们也是 166，W732 已实核 MI50 32 GB = `05:00.0` = `card0` = `renderD128`。-> routeK 的**指令级实测**可移植性高。
3. **routeK 真正可移植的资产是三类东西，都不是「算法代码」**：
   **① 40+ 个 gfx906 微基准探针**（`benchmarks/kernels/gfx906/`）
   **② 3 个 gfx906 技能**（ISA 反汇编 / 显存归因 / rocprofv3 kernel trace）
   **③ `docs/gfx906/` 89 份 + 一张实测的 dot 指令速率表**。
4. **最值钱的一条是那张速率表**（`docs/gfx906/dequant-instructions.md`，2026-08-28 实测，MI50/ROCm 7.14）：
   `v_dot4_i32_i8` = 25,877 GMAC/s（4.44x fp32）= gfx906 **唯一**可用的 int8 dot；
   `v_dot8_i32_i4` = **49,600 GMAC/s（8.52x fp32 = 3.75x packed fp16）**，**原生 packed-nibble、无解包 ALU**。
   **而反面那两行才是关键**：`i4->i8 解包 + 2x sdot4` = **1,375（0.24x）**、
   `i8->half2 展开 + 2x fdot2` = **1,002（0.17x）**。**[routeK实测]**
5. **由此得到一条可以直接用到 Strata 上的判据**：Strata 的 IQ4 内循环是
   「每 4 个权重 **5 个位操作** + 1 次 `dp4a`」（`iq_kernels.cu:506-517`）**[Strata源码]**
   -> 它正落在 routeK 实测**最慢的那一格**（解包 + dot）。而原生 nibble 的 `v_dot8_i32_i4` 是那一格的
   **36 倍**。**这就是 T5 的靶子，而且靶子就在我们自己身上。**
6. **第二条可直接用的判据**：布局类改动**只在 multi-token / issue-bound 一侧赚钱**
   （第三方 dp4a Q8_0 重排实测：单 token 中性 `-1.1~+6.4%`；**multi-token `+21~+51%`**）**[routeK实测+文档]**
   -> Strata 的布局类工作应押 **预填**（chunk 8192，multi-token），不押 decode。
7. **本项目当前负载的瓶颈仍不在算力面**：W721 份额表（本项目实测）多轮时**重复预填约 90%**。
   -> 上述移植**不改这个结论**，只改「算力面还有没有空间」的答案：**有，但押在预填侧，且要先有门**。

---

## §0.5 更正与本波自认（第一次错在哪）

| # | 初版写了什么 | 主源实际是什么 | 性质 |
|---|---|---|---|
| 1 | 「routeK 的 T5：`v_dot8_i32_i4` = 49,600 GMAC/s = 3.75x packed fp16」--**只有这一行，且未说它是文档值还是实测值** | 主源 `dequant-instructions.md` 有**完整速率表**：`v_dot8_i32_i4` = 49,600 / **8.52x fp32** / FULL RATE / 原生 packed-nibble。**是实测**（SCEV-proof 探针 + best-of-7 hipEvent） | **不实（单薄）**：数字对，但漏了「8.52x fp32」这个更硬的分母，也漏了**反面三行**（0.24x / 0.17x），而那三行才是对 Strata 最有用的 |
| 2 | 把 `dot_isa_probe.py` 的「`v_dot8_i32_i4` 存在但需要 i4 操作数」当成「routeK 从未测过它」的旁证 | 两处记录**都对**：速率表证明**能发出且满速**；`dot_isa_probe` 说的是**它对 Q8 的 i8x i8 用途无用**。**我把「对他们无用」误读成「没测过」** | **误读** |
| 3 | 未提 `v_dot2_f32_f16` 这条**已被 routeK 自己用 objdump 推翻**的候选 | 主源有完整的更正链（`SUPERSEDED` 段 + `2026-08-29` objdump 复核）：生产内核 P·V 已是 `1024x v_pk_fma_f16` = 1 指令 / 2 MAC -> dot2 重写**收益为零**，只是精度改动 | **漏项（且正好是我最该看的那类）**：它给出的教训「**源码写法 != 实际发射**」直接否掉我在 §2 里那条「Strata 的 `fused_gr` 是展开的 8 个 fmaf」（那是**读注释**得出的） |
| 4 | 把 routeK 的资产说成「T1/T5 两条 OPEN + 一张排除表」 | 真资产是**一整套探针库 + 技能包 + 89 份 docs**；T1/T5 只是其中两条 | **低估** |

**过程缺陷（同族第 N 次）**：我把「归档件」当成了「原始证据」。这与项目铁律第一条冲突。**归档件是覆盖式的、允许滞后的**；
主源是树。-> 已写成文：**引用 routeK 必须读 routeK 的树，不得只读 `ARCHIVE.md`**。

---

## §1 两边的关系（源码确证）

| | routeK | Strata（本项目） |
|---|---|---|
| 树 | `166:/home/albus/routeK/src` = vLLM fork（顶层含 `csrc/` `vllm/` `setup.py` `rust/`） | 0.1.41，`src/program/generate.cpp` 12,149 行 + `src/kernels/cuda/*.cu` |
| 同名内核 | `fused_gr` **0** / `s2_expert_grouped` **0** / `native_mmvq` **0** / `iq_kernels` **0** | 四个都在 |
| 内核总数 | `src` 下 `.cu/.cuh/.hip` **239 个**（含 `build/` 拷贝；实源码见下） | - |
| 实源码内核目录 | `csrc/gfx906_fa/kernel/`（`fattn-q8.cuh` 57 KB · `ggml_shim.cuh` · `q8_0_quantize.cuh`）、`csrc/rocm/`（`dense_gemv_gfx906.cu` · `moe_q_gemm_gfx906.cu`）、`csrc/libtorch_stable/{gdn,moe,quantization,attention}/` | - |
| 形态 | 27B dense + 35B-A3B MoE，64K，c1..c16 吞吐 | 125B MoE `huihui-ud-iq4_xs`，262,144 ctx，专家全驻 RAM（76 GiB） |
| 分辨力（本项目已定） | - | 预填 **1.2~1.7%** · 解码 **9.5~15%** |

-> 可移植性判据：**指令/微架构/工具/规程** 可搬；**代码与模型级百分数** 不可搬。

---

## §2 routeK 的真资产清单（本次新发现的主体）

### 2.1 `benchmarks/kernels/gfx906/` -- 40+ 个微基准探针（**与引擎解耦**）

按名列出（`ls` 实测，节选）：

| 类 | 文件 |
|---|---|
| **ISA / 指令** | `dot_isa_probe.py` · `int8_triton_dot_probe.py` · `int8_gemv_probe.py` · `bench_w8a16_gfx906.py` · `bench_t1_m4_gfx906.py` |
| **GEMM/GEMV 几何** | `bench_moe_gemm_gfx906.py` · `bench_dense_gemv_gfx906.py` · `bench_dense_gemv_k5120.py` · `bench_llmm1_rows_per_block.py` · `bench_fp16_m4.py` · `bench_fp16_skinny_m.py` · `bench_awq_m_scaling.py` · `gemm_step_census.py` |
| **FA / 注意力** | `bench_gfx906_fa_decode.py` · `..._fa_gather.py` · `..._fa_tile_clip.py` · `fa_capture_replay_probe.py` · `fa_cfg_sweep.py` · `fa_nantail_probe.py` · `fa_persist_probe.py` · `fa_tailcost_probe.py` · `fa_m4_splitk_accuracy_probe.py` |
| **"孤岛 harness"** | `harness/moe_m1_harness.cu` · `harness/topk_harness.cu` |
| **逐内核归因** | `kernel_prof_probe.py` · `gdn_step_spy.py` · `gemm_step_census.py` · `c1_routing_structural_probe.py` · `mtp_shape_spy.py` |
| **其它** | `legacy0_b1_step_probe.py` · `legacy0_append_cost_probe.py` · `moe_spec_ab.py` · `moe_multireq_ab.py` · `greedy_probe.py` · `batchdesc_probe.py` · `g1_node_replay_probe.py` · `gemma4_*_probe.py` |

**为什么这是「可移植资产」**：它们测的是**这张卡的指令与几何**，不依赖 vLLM。
搬过来只需要改「怎么把被测内核拿出来」那一段（Strata 是 `.hip_fatbin` / `build-906/`）。

### 2.2 `.agents/skills/` -- 3 个 gfx906 技能（**规程直接可用**）

| 技能 | 描述（frontmatter 逐字摘要） | 对本项目的用处 |
|---|---|---|
| `gfx906-isa-disassembly` | 「Extract and disassemble the gfx906 (amdgcn) GPU code of vLLM custom kernels... **when a perf claim rests on what the compiler actually emits: instruction fusion (e.g. half2 a*b+c into packed FMA), dot-instruction usage, per-kernel instruction counts, or whether a gfx906 ISA instruction exists at all.** Validated 2026-08-29」 | **正是我们判「某内循环能不能换更强指令」所缺的能力**（见 §4-P1） |
| `gfx906-mem-attribution` | 「Attribute peak GPU-memory transients (startup / first-prefill OOMs)... **an OOM traceback names an innocent-looking allocation frame (it is the last straw, not the owner)**... Validated 2026-08-27/28 (per-impl q_pad OOM root cause)」 | 我们 262,144 ctx + 76 GiB 驻留下的显存瞬态归因 |
| `gfx906-rocprofv3-kernel-trace` | 「Profile vLLM/torch GPU kernels... **when torch-profiler/kineto GPU traces come up empty**... Records the verified-working invocation, the vLLM multiprocess failure mode, and the focused-microbench workaround. Validated 2026-09-11」 | 我们有 `--stage-timing`（**stage 级**），**kernel 级归因没有工具** |

可复用的**命令链已写在主源里**（`dequant-instructions.md`）：
`gfx906_fa_launcher.hip.o` -> `.hip_fatbin` -> `clang-offload-bundler -unbundle -type=o` -> `llvm-objdump -d`。

### 2.3 `docs/gfx906/` 89 份 + `csrc/` 里的可对照实现

- 89 份 DEVLOG/plan，含 `int8-investigation-qwen.md`（**48,753 B**，int8 总台账）、`dequant-instructions.md`（8,174 B）、`lds-layout.md`、`latency-hiding.md`、`dvfs-mi50.md`、`prefill-multibatch-tax.md`、`degradation.md`（137 KB）、`plan-gfx906-fa-fix.md`（33 KB）。
- `csrc/libtorch_stable/gdn/fused_gdn_decode_kernel.cu`（**24,345 B**）-- **GDN 是两家共有的模型组件**
  （Strata 有 `--native-gdn` / `--no-fused-gdn`）。配套 `gdn_step_spy.py`（逐 step 打印 48 层 GDN 走了哪条路径）。
- `csrc/libtorch_stable/quantization/` = `w8a8/{cutlass,fp8/amd,fp8/nvidia}` + `utils.cuh`（**T1/A8W8 的真身**）。
- `csrc/moe/` 只有 `dynamic_4bit_int_moe_cpu.cpp`（**CPU 侧** 4bit MoE）；GPU 侧 MoE 走 vLLM 自带。

---

## §3 芯片级结论：routeK 实测的 dot 指令速率表（**本节是全文核心**）

出处：`166:/home/albus/routeK/src/docs/gfx906/dequant-instructions.md`「Measured dot-instruction rates
(2026-08-28, MI50, ROCm 7.14 clang 23)」。方法：SCEV-proof 探针（旋转 dot 输出喂下一轮输入，整数递推无法被编译器闭式化）；
960x256 线程填满 60 CU；best-of-7 `hipEvent`；ISA 发射用 `-S` dump 验证。

| op | GMAC/s | vs fp32 FMA | 读数 |
|---|---|---|---|
| fp32 FMA（`v_mac_f32`） | 5,824 | 1.00x | 1 MAC/lane/cycle 基线 |
| packed half2 FMA（`v_pk_fma_f16`） | 13,210 | 2.27x | 满 packed 速率，2 MAC/cyc |
| `v_dot2_f32_f16` | 3,349 | 0.58x | 延迟链探针下限；ILP >= 2 时约 10 T |
| **`v_dot4_i32_i8`** | **25,877** | **4.44x** | **FULL RATE，4 int8 MAC/lane/cyc**（AMD 给 MI50 的 53 TOPS INT8 就是这条） |
| **`v_dot8_i32_i4`** | **49,600** | **8.52x** | **FULL RATE，8 i4 MAC/lane/cyc，原生 packed-nibble 操作数，无解包 ALU** |
| i8 -> half2 展开 + 2x `fdot2` | 1,002 | 0.17x | 展开（约 2.5 VALU ops/元素）把收益杀光，比裸 dot4 慢 **25x** |
| **i4 -> i8 解包 + 2x `sdot4`** | **1,375** | **0.24x** | **解包不可摊销；相对原生 `sdot8` 是空谈** |

主源给出的三条推论（逐字要点）：
- **「There is no int8 dot gap.」** `v_dot4_i32_i8` 已是可用的最快 Q8 内循环指令（packed-fp16 MAC 速率的 2 倍）；
  任何「用 fp16 dot2 做精确 Q8」的方案都输（见展开那一行）。
- **「`v_dot8_i32_i4` is the one genuinely faster dot」**（dot4 的 2 倍 MAC 速率、操作数字节减半）
  **但它要求两个操作数都是 i4 数据（这是 Q4 格式变更，不是指令替换）。**
- 指令吞吐随频率缩放（探针跑在约 1.5 GHz），**比值与频率无关**。

**可用性边界（`dot_isa_probe.py` 的 VERDICT + `dequant-instructions.md` 的 caveat，两处一致）**：
- 编译到 **object**（跑 llvm-mc 校验）才是否可用性的答案：gfx906 的 int-dot 集合 = **`{v_dot4_i32_i8}` 一个**。
  `v_dot4c_i32_i8` = 「instruction not supported on this GPU (gfx906)」；`v_dot8_i32_i8` / `v_dot8c_i32_i8` = 「invalid instruction」。
  **三者都能过 ISel，但被汇编器拒；`-S` 输出不是可用性答案。**
- `v_dot8_i32_i4` 是 **i4 变体（packed-nibble 操作数）**，**存在**；
  主源判定它对 Q8 的 i8 x i8 用途「irrelevant」--**不是不存在、不是打不出、不是没测**。
- gfx906 **没有 `v_mfma*`**（无 MFMA）。SDWA 只能选字节/字子通道，不能做任意位域。

---

## §4 三条可直接落地的移植（按「先做哪个」排序）

### P1 **移植 ISA 反汇编规程到 Strata 的构建产物**（零风险、最高优先）

- 理由：routeK 用这条**推翻了自己的一条候选**（见 §0.5-3）。原文逐字：
  「**FA-Q8 P·V -- the dot2 rewrite's instruction-halving premise is REFUTED against the built kernel (2026-08-29)**...
  the P·V accumulate in `flash_attn_tile_q8<128,128,16,2>` is **1024x `v_pk_fma_f16`**... against **0x `v_pk_add_f16`**.
  The source's half2 ops contract to the packed FMA under the default fp-contract」
  -> **源码里写 `VKQ += v * p`，实际发出的是 packed FMA；只读源码会得出「能减半指令数」的错误结论。**
- **对 Strata 的直接后果**：我在初版里依据 `fused_gr.cu` 的**注释**（「the same eight fmaf in the same order」）判定
  「Strata 的 grouped-rows 内循环是展开的 8 个 fmaf」-- **这正是 routeK 犯过的同型错误的现场**。
  **该结论在 objdump 之前不得引用。**
- 可搬的东西：技能 `gfx906-isa-disassembly` 的规程 + 命令链（`clang-offload-bundler -unbundle` -> `llvm-objdump -d`）。
- 判据：能在 Strata 的 `build-906/` 产物上取出某内核的 SASS/amdgcn 列表并数出指令构成。

### P2 **int4 原生 nibble 路径（T5）--靶子就在 Strata 的 IQ4 内循环上**

- **Strata 现状（[Strata源码] `iq_kernels.cu:506-517`）**：IQ4_XS 的 vec-dot 是
  ```c
  int vi0 = (vl >> 0) & 0x0F0F0F0F;          // 1
  vi0 |= (vh << 4)  & 0x00000010;            // 2
  vi0 |= (vh << 11) & 0x00001000;            // 3
  vi0 |= (vh << 18) & 0x00100000;            // 4
  vi0 |= (vh << 25) & 0x10000000;            // 5
  sumi = ggml_cuda_dp4a(vi0, u0, sumi);      // 每 4 个权重一次 dp4a
  ```
  = **每 4 个权重：5 个位操作 + 1 次 dp4a**（`u` 是 int8 激活）。**[Strata源码]**
- **routeK 的对应格**：`i4 -> i8 解包 + 2x sdot4` = **1,375 GMAC/s = 0.24x fp32**；
  **原生 `v_dot8_i32_i4` = 49,600 = 8.52x**。两者相差 **36 倍**。
- -> **判据（可执行）**：Strata 的 IQ4 路径若不能改成原生 packed-nibble，就永远停在「解包」那一格；
  要动，**必须两边都是 i4**（这是格式变更，不是换指令）。routeK 已经把这条判据说死了：
  「it requires i4 data on BOTH operands (**a Q4 format change, not an instruction swap**)」。
- **必须先做的三步（全零成本）**：
  1. 用 P1 的工具量出 Strata IQ4 内循环的**实际指令构成**（5 位操作是否真被发出）；
  2. 用 routeK 同款 SCEV-proof 探针在**本引擎的构建环境**里复测 `v_dot8_i32_i4` 的 49,600（确认不是另一套 toolchain 的结论）；
  3. 只有前两步都成立，才谈「激活也量化到 i4」--**那要质量门，且一票否决 = 改答案**。
- **旁证（Strata 自己有先例）**：`--kv q4_0` = 「4-bit codes **after a Hadamard rotation**」（`kv_q4.hpp`）
  -> 本引擎在「4-bit 码本 + 旋转」上有实现与验收路径。
- **一票否决**：破位一致 / 改答案；**路由K 的纪律**：**probe 前不许构建任何东西**。

### P3 **布局类改动押预填侧（multi-token），不押 decode**

- 出处：`dequant-instructions.md`「Layout-change outcomes measured on real gfx906 (third-party, 2026-08-28)」--
  第三方 `mxxm-t/mx-llama.cpp` PR #4（dp4a-based Q8_0 权重内核，两平面布局：连续 int8 quants 平面 + 独立 f16 scale 平面）：

  | regime | 我们的对应物 | 布局改动增益 |
  |---|---|---|
  | single-token mat-vec（weight streaming, **byte-bound**） | B=1 decode / FA loader | **中性（-1.1 ~ +6.4%）** |
  | multi-token GEMM（LDS-staged, double-buffered, **issue-bound**） | **prefill / spec-decode Sq>1** | **+21 ~ +51%** |

- 主源结论逐字：「**Layout work does not pay on byte-bound single-token streaming paths**...
  Price layout changes for the multi-token/issue-bound side of the stack, or don't price them at all.」
- -> **对本项目**：`--prefill auto`（本机 chunk 8192）是 **multi-token** 侧 -> 布局/权重重排类改动**有量级**；
  decode（单 token）侧**别投**。
- 可搬的机制：scale 作为独立 `uint16` 平面的掩码读法（`*dp & rmask`）、GEMM 路径的 k-major scale LDS 暂存（`sWdh`）。
- **限定**：第三方场景是 write-once 静态权重，比 KV-cache 别名宽松。

---

## §5 routeK 的排除表（能省掉重复试错）

**等级：routeK 实测（同机同卡）+ 我本轮源码/文档核对。**

| 判定 | 机制（逐字要点） | 对本项目的处置 |
|---|---|---|
| **不存在「换更好的 dot 指令救 B=1 decode」** | `v_dot4_i32_i8` **已在内循环且满速**（4.44x fp32，绝对速率 25,877）；B=1 是 gather-HBM 受限 | **直接把这一整类划掉**。Strata 的 dp4a 位置我已 [Strata源码] 核过：`iq_kernels.cu:537` / `native_mmvq.cu:200,548` / `s2_expert_grouped.cu:96,309,415`；HIP 下 `STRATA_DP4A` = `__dp4a`（`dp4a.hpp:17-19`） |
| **不存在「靠消寄存器溢出救 kernel」** | 全部在树 HIP 死路 standalone 编译读回 HSA notes：**`vgpr_spill_count` 全 0**；死因全是结构性的 | **芯片级**，与引擎无关。省掉一整类排查 |
| **`lm_head` GEMV 已在 HBM 地板**（3114 vs 3128 us） | 「lm_head GEMV 杠杆」不存在 | 不在 lm_head 上找收益 |
| **A8W8（i8 激活 x i8 权重）prefill 范围受限** | Triton `tl.dot` 路径：A 过（dot4 发出、精确、指令数正好是等工作量 fp16 内核的**一半**）**但 C 只有 hipBLAS fp16 的 0.59~0.68x**（Triton 只达 dot4 record 的 19%）-> **编译器差距超过 int8 的 1.96x 优势** = NO-GO | 「改成 int8 内核」的收益上限**先算 MAC 占比与编译器落地率** |
| **`v_dot2_f32_f16` 重写 = 零收益** | 生产内核 P·V 已是 `1024x v_pk_fma_f16` = 1 指令 / 2 MAC（**0x `v_pk_add_f16`**）-> dot2 也是 1 指令 / 2 MAC -> 只买精度，不买指令数 | **否决「dot2 重写」这条直觉**；并要求先 objdump |
| **原生 `v_dot4_i32_i8` 已是 Q8 的终点** | 「There is no int8 dot gap」；Q·K 侧无可动的指令升级 | 别在 Q8 内循环上找 ALU 收益 |
| `STRATA_GR_SPLIT`（K 向拆分）约 3% / **破坏位一致** | 「sums in another order than the single-token read, so off by default」（`AMD_HIP.md:482` 与 routeK 判读一致） | 我们已据此把 P28 判 REJECTED（W720），**两边一致** |
| **同一台机存在「主机态退化」** | 一条判决被撤回：`RETRACTED - the "regression" was host-state degradation`；根因定为 HIP 默认的 **active-wait 调度** + `deterministic host-level defect`（跨配置复现） | **同机同卡** -> 我们每次 A/B **必须记主机态**（是否刚重启 / Z0 档 / 是否刚跑过重负载 / 是否刚收过车）。**这条直接补我们的口径** |
| SD-gram（GPU n-gram proposer）= 非采纳 | GPU **0.428** vs CPU **1.08** accepted/draft-step | 对 Strata 的 `--lookup-chain` / `--suffix-draft` 给**低期望值先验**（**不构成否决**：不同实现、不同语料，Strata 的 lookup 在 CPU 侧、成本模型不同） |

---

## §6 方法论闸门（routeK 用血换的，可直接搬）

| # | 闸门 | 主源依据 | 我们的现状 |
|---|---|---|---|
| C1 | **判死三步**：找当次失败日志 -> 抽**原始异常行** -> 看代码此后是否改过 | dflash2 曾因两车 `ALL FAILED` 被判整条线弃，回查才发现根因只有一行且当天已修 | 我们实践过近似的（W720「读源码即判」）；建议成文进 §1 |
| C2 | **孤岛 harness 的赢不传导到服务 wall-clock**；服务态 graph A/B 才是闸门 | ARCHIVE §4.2 三条反复教训 | 与我们的「分辨力」口径互补 |
| C3 | **PPL 在 hybrid attention 上不可靠** -> 连贯文本 + logprob A/B | 同上 | Strata 也是 hybrid（有 GDN）-> **直接适用**；**否掉「用 PPL 判 `--kv` 四档」** |
| C4 | **默认关 != 不可达**；判可达性须核宏 | routeK `T297` | 我们在 P30/P28/P29 已同源 |
| C5 | 跨时代/跨口径数字一律不可相减 | ARCHIVE §2 铁律 | 我们的「预填两口径不可混比」同源 |
| **C6** | **源码写法 != 实际发射；结论必须落在 objdump 上** | `dequant-instructions.md` 的 `SUPERSEDED` + 2026-08-29 objdump 复核 | **本次新增**，见 §4-P1 |

---

## §7 Strata 自身的未探索面

### 7.1 旋钮面已基本收敛

- register 50 行：**ADOPTED 24 / REJECTED 25 / CANDIDATE 1**。
- 现役生产 args 只有 **16 项**（`--pack / --native / --resident-budget-gib 76 / --expert-profile / --expert-cache auto / --pcie-frac 0.20 / --spec 4 / --spec-min-p 0.70 / --mtp / --max-context 262144 / --kv k8v4 / --prefill auto / --prompt-cache-every 8192 / --expert-profile-save / --conversation-cache-mib 4096 / --vision`）+ 2 env。**[Strata源码]**
- **但**源码里共 **167 个 CLI 长选项** 与 **76 个 `getenv("STRATA_*")`**（`generate.cpp` 单文件口径）-> register 覆盖是**稀疏的**。

### 7.2 四个未覆盖面

| 面 | 具名旋钮（未登记） | 为什么 |
|---|---|---|
| **drafter/投机** | `--suffix-draft`（**默认 3**）、`--lookup-chain`(0~7) + `--lookup-chain-min`、`--window-hashes`、`--coupled-draft`/`--no-coupled-draft`、`--mtp-max-t`、**`--mtp-q4`**、`--mtp-draft-vocab`、`--mtp-hnorm`、`--spec-split`/`--no-spec-split`、`--spec-follow` | **W715 已记「`--lookup-chain` / `--mtp-max-t` 未启用·可选增强，本次未开」** -> 已识别未做。且我们**从不量接受长度**，而 routeK 的结论说 MTP 划不划算全看它（回本线 2.0） |
| **KV 质量门** | `--kv` 的另外三档：`fp16`(默认) / `int8` / `q4_0`（Hadamard 旋转后的 4-bit 码） | P04 只记「k8v4 = ADOPTED，816 B/cell vs int8 1056」，**没有质量数字** |
| **取数/IO** | `--pcie-mode`(`auto`/`dma`/`kernel`/`direct`)、`STRATA_IO_PREFETCH`、`STRATA_IO_PF_THREADS`、`STRATA_IO_PF_STAGE`、`STRATA_IO_PREFETCH_DEPTH`、`STRATA_FILL_AHEAD`、`STRATA_FS_AHEAD`、`STRATA_FS_SLOTS`、`STRATA_FETCH_THREADS`、`STRATA_UNBUFFERED_LOAD`、`--short-read`、`STRATA_SSD_KEEPALIVE*` | 现役只调了 `--pcie-frac 0.20`。**预期低**（专家全驻 RAM，份额表说专家搬运约 0） |
| **会话/驻留/CPU** | `--conversation-cache-slots`、`--conversation-cache-min-free-mib`、`--prompt-cache-root`、`--prompt-cache`、`--session-min-free-mib`、`--resident-experts`、`--resident-cpu-experts`、`STRATA_RESIDENT_HEADROOM_GIB`、`STRATA_RESIDENT_PIN`、`--host-core`、`--pool-affinity`、`--pool-tasks` | P31 只动了 `--conversation-cache-mib`；W735 已证 `evictions` 真的会到 5 ->「预算够」非恒真 |

### 7.3 已核实「不适用/不可达」，别再查

| 项 | 核实方式 | 结论 |
|---|---|---|
| `STRATA_MMVQ_IL` | 引擎二进制实存 `native_q8_1_interleave is CUDA only`；源码整块在 `#if !defined(__HIPCC__)` 内，HIP 侧 `native_mmvq_il_supported()` 直接 `return false` | P30 成立。注意：上游 `docs/MMVQ_IL_TABLE.md` 明写「给新卡测表 -> 贴 issue -> 维护者并入 `kIlArch`」，即 **gfx906 本来就没有表**；这是**上游官方流程**的贡献口，不是 bug |
| `STRATA_HIPBLASLT_TUNING` / `STRATA_HIP_WMMA` | 容器有 `libhipblaslt.so.1.4`；**引擎二进制 0 处 hipblaslt 字符串**；`tools/hip/` 表只有 gfx1100/gfx1150/gfx1151/gfx1200/gfx1201，**无 gfx906** | P96 成立。-> 上游那些 +27% / +31.9% 的 hipBLASLt 收益与我们无关 |
| `--vram-elastic` | help 明写 NVIDIA；源码 `--vram-elastic ... is CUDA-only for now` | P95 成立 |
| `STRATA_STAGER_SSD` | register P98 三臂差 <=0.1% | 已判无收益 |

### 7.4 上游自己承认的空白（对本项目最有利）

`docs/AMD_HIP.md:504` 逐字：**「Not done: setup.py detection and an automatic build, Windows, images (`--vision`),
MI60 and Radeon VII, **a single-card run**, the tensor-split experiment.」**

-> 上游 gfx906 的公开读数**全部来自 `2x MI50 16 GB` + `--layer-split 27`**（`AMD_HIP.md:489-502`：
17,043-token prompt 43.5 s / 392 tok/s、decode 57.7~59.3 tok/s，Coder IQ1_M、131,072 ctx、
`--kv int8 --kv-resident 32768 --prefill 4096 --spec 4 --spec-min-p 0.5 --pcie-frac 0 STRATA_ARENA_MMAP=1`）。

**而本项目跑的正是「a single-card run」**（单张 MI50 32 GB，专家全驻 RAM，262,144 ctx，IQ4_XS）。两条推论：
1. **我们的单卡读数本身就是上游没有的数据点**（零成本可贡献）。
2. 上游那台机有一组参数我们**没试过**：`--prefill 4096`、`--spec-min-p 0.5`、**`--pcie-frac 0`**、`STRATA_ARENA_MMAP=1`。

---

## §8 候选清单（修订版）

| # | 靶子 | 预期 | 成本 | 风险 | 判据 / 一票否决 |
|---|---|---|---|---|---|
| **R1** | **移植 ISA 反汇编规程**（P1）到 `build-906/` 产物 | 高（它是**所有**内核级结论的前置） | 低 | 无（只读） | 能取出某内核的 amdgcn 列表并数出指令构成；**在它之前，任何「某内循环可以换更强指令」的判断不得引用** |
| **R2** | 量出 **Strata IQ4 内循环的实际指令构成** + 在本 toolchain 复测 `v_dot8_i32_i4` 速率 | 高（决定 T5 是否值得碰） | 低 | 无（只读探针） | 报出「每 4 权重几条位操作 + 几次 dp4a」与 `v_dot8_i32_i4` 的本机 GMAC/s |
| **R3** | **接受长度**（MTP 的 roi 参数） | 高（最硬的信息） | 极低 | 无 | 报出 `draft_accepted / draft_offered` 与均长；**并记录负载类型**（合成 vs 真实） |
| **R4** | `--kv` 四档的**质量门** | 不是提速，是补一把尺 | 中 | 低 | **KLD 为主门**；**禁 PPL 单独做门**（C3）；连贯文本 + logprob A/B 为辅；同车并读速度 |
| **R5** | `--mtp-q4`（`proj`/`head`/`all`） | 中 | 低 | 低 | **R3 过了 2.0 才做**，否则只记「条件项」 |
| **R6** | drafter 的查找式草稿：`--lookup-chain` + `--suffix-draft` | **低**（routeK SD-gram 先验 0.428 vs 1.08） | 低 | 低 | 同 R3 的接受长度 + 解码 t/s |
| **R7** | 布局类改动（P3）押**预填侧** | 中高（第三方 +21~51% 是 multi-token 侧） | 中高 | 中 | 预填 t/s（分辨力 1.2~1.7%），**必须同车记 `chunks`** |
| **R8** | 把**单卡 gfx906** 读数整理成对上游的贡献 | 零收益、有外部价值 | 低 | 无 | 补上游 `Not done: a single-card run`；与 W736 的 #1731/#1732/#1733/#1734/#1735 同渠道 |

---

## §9 建议顺序

**R1 -> R3 -> R2 -> R4 -> R5 -> R6 -> R7 -> R8**

- **R1 必须最先**：没有它，R2 与任何「内核可改进」的判断都是**读注释**级别的（§0.5-3 就是现场）。
- **R3 与 R4 是「门」**：没有它们，后面每个变体的收益都不可判。
- **R2 零成本零风险**，且能一次答清 T5 值不值得碰。
- **R6/R7 放后面**：份额表已说专家搬运约 0、SD-gram 先验低。

**期望管理（不改结论，只改期望）**：本项目当前负载瓶颈是**重复预填（约 90%）**，
而 routeK 的算力面资产作用在**单次前向的计算密度**上。-> **最大的那块仍在缓存/会话面**
（P31 已是 -93.0%，还有 `--conversation-cache-slots` 等未动）。

---

## §10 我不能确定的（诚实账）

1. **routeK 的内部记录有一处张力，必须读全文才不误判**：`dequant-instructions.md`（2026-08-28）把
   `v_dot8_i32_i4` 列为**实测 49,600 GMAC/s / FULL RATE**，并用 `-S` dump 验证 ISA 发射；
   而 `dot_isa_probe.py`（后写）说 **`-S` 不是可用性答案**、object 级只有 `v_dot4_i32_i8` 被接受。
   我读全文后的理解是**两者不矛盾**：`v_dot8_i32_i4` 能发出且满速，只是对 Q8 的 i8xi8 用途无关。
   **但这条我未在 routeK 的其它件里交叉确认**（`_verdicts.md` / `DEAD-ENDS.md` 未读）。
2. **routeK 的百分数一条都不迁移**：`+10~13%` / `+14~19%` / `8.52x` / `4.44x` 中，
   **速率表那两行是芯片级、可迁移**（同一张卡、同 toolchain 家族）；**服务级百分数是模型级、不可迁移**。
3. **我没做**：Strata 侧「预填/解码/专家搬运/KV」的**新测份额表**（沿用 W721）。
   R1/R3 之后若要排 R6/R7，应补一次本项目自己的份额表（routeK 的 `gemm_step_census.py` / `gdn_step_spy.py` 方法可照搬）。
4. **Strata 的 IQ4 内循环「5 位操作」是否真被发出，我没 objdump 过**--正是 §4-P1 要说的事；本件里它是**源码读数**，不是发射读数。
5. **`--lookup-chain` 等 drafter 开关的默认语义我只读到解析行与 `int suffix_draft = 3`**，未读完 `sfx_on` 全部作用路径 -> R6 执行前需一次源码级可达性判定（按 C4）。

---

## §11 落盘与出处

- 本件：`deploy/W737_ROUTEK_PORT.md`（**修订版**；初版留档 `W737_ROUTEK_PORT.md.bak_v1`，23,953 B / md5 `2334de36b17a`）
- **routeK 主源（本轮实读，`ssh albus@192.168.50.166`）**：
  `src/docs/gfx906/dequant-instructions.md`（8,174 B，**速率表全文** + 第三方布局实测 + dot2 更正链）·
  `src/benchmarks/kernels/gfx906/dot_isa_probe.py` · `src/benchmarks/kernels/gfx906/int8_triton_dot_probe.py` ·
  `src/benchmarks/kernels/gfx906/bench_w8a16_gfx906.py` · `src/benchmarks/kernels/gfx906/gemm_step_census.py` ·
  `src/benchmarks/kernels/gfx906/gdn_step_spy.py` · `src/csrc/gfx906_fa/kernel/{fattn-q8.cuh,ggml_shim.cuh}` ·
  `src/csrc/libtorch_stable/gdn/fused_gdn_decode_kernel.cu` · `src/vllm/gfx906_fa/gfx906_fa_backend.py:579-634,934-975`（**arm1/arm2 源码坐实**）·
  `src/.agents/skills/{gfx906-isa-disassembly,gfx906-mem-attribution,gfx906-rocprofv3-kernel-trace}/SKILL.md` ·
  `src/docs/gfx906/`（89 份）· `src/csrc/{quantization,moe}/`（清单）
- **routeK 归档件（仅作对照，本版不再单独作为证据）**：`D:/workbuddy/_z_src/ARCHIVE.md`（1,208,977 B / 14,138 行）
- **Strata 侧（本机 0.1.41 源码树 `deploy/tmp/src411/Strata-0.1.41`）**：
  `src/kernels/cuda/iq_kernels.cu:506-517,537` · `native_mmvq.cu:200,548` · `s2_expert_grouped.cu:96,309,415` ·
  `fused_gr.cu`（`dot8u(Bf16x8,float4,float4)`，**注释口径，待 objdump**）· `include/strata/kernels/dp4a.hpp:17-19` ·
  `src/program/generate.cpp`（167 CLI / 76 env / `mtp_q4` / `--kv` 取值 / `suffix_draft = 3` / `pcie_mode`）·
  `docs/AMD_HIP.md:473-506` · `docs/MMVQ_IL_TABLE.md` · `tools/hip/*hipblaslt*.txt`
- **本项目现状**：`deploy/params/PARAM_REGISTER.tsv`（50 行）· `deploy/params/generated/strata-huihui-ud-iq4_xs.json` ·
  `deploy/W713_PLAN.md` §6 · `deploy/W715_HUIHUI_SWITCH.md:139-140` · `deploy/W721_VIEW.md` · `deploy/W708d_PARAM_SOLIDIFY.md:62`
- 166 只读核实：容器 `strata166-407` 内 `strings /src/build-906/strata`（`native_q8_1_interleave is CUDA only` 实存；`hipblaslt` 计数 0）· `/opt/rocm/lib/libhipblaslt.so.1.4` 在位
