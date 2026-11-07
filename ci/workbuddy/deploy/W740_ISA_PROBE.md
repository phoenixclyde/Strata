# W740 ISA 探针 + 接受长度（R1 / R2 / R3）

> 波次：2026-10-10 00:45 ~ 01:2x（承接 W739）。
> 起因：机主问「routek 为什么要反汇编？直接去 ki 的 GitHub 看源不行吗？源码 166 就有」，
> 并给出自有库 `phoenixclyde/vllm-gfx906-mobydick`。
> 本轮把候选表 W737 §8 的 **R1 / R2 / R3** 做掉。

## 0 「为什么要反汇编」--第一方答案（就在我们自己的库里）

**上游库 = `KIntegrated/vllm-gfx906-mobydick`**（`kintegrated` 即此），我们是 fork
`phoenixclyde/vllm-gfx906-mobydick`。库里有**我们自己的技能**
`.agents/skills/gfx906-isa-disassembly/SKILL.md`（分支 `gfx906-patches-030`）。它的 frontmatter 逐字写：

> Use when a perf claim, review finding, or conflict between committed records rests on
> **what the compiler actually emits**: instruction fusion (e.g. half2 a*b+c into packed FMA),
> dot-instruction usage, per-kernel instruction counts, or **whether a gfx906 ISA instruction exists at all**.

正文三条铁律，逐字：

- **「"Two source ops" is NOT evidence of two instructions - disassemble.」**
- **「Availability gate = compile-to-object, not `-S`」**
- **溯源**：*「A dump is only as good as the build it came from. Record the commit + `.so` mtime alongside every count; re-extract from the current build before citing. A review rejected a refutation built from a parked, unmerged branch's dump.」*

`Worked case` 节记的正是**读源给出错误答案**的那次（2026-08-29 M3 review F1）：
路线图与 `dequant-instructions.md` 对「FA-Q8 的 P·V 是 `v_pk_fma_f16` 还是 mul+add」**说法冲突**，
一次 offload-bundle objdump 定了案（fused FMA），**败方记录标 SUPERSEDED**。

-> 结论：**反汇编不是拿来代替读源的**。读源答「算法/意图/开关/哪个内核存在」；
反汇编答三件源答不了的事：(1)编译器**实际发射**了什么；(2)这张卡**能不能编码**某条指令；
(3)跑的这份二进制**与源是否同一份**。routeK 之所以做，是因为第 (1) (3) 两条在那次是**胜负手**。

routeK 那次的反汇编对象是 `_rocm_C.abi3.so`（**预编译扩展**），且它最有价值的一条
（`v_dot8_i32_i4` 可用）其实来自 `llvm-mc -show-encoding`（**汇编探针**），不是反汇编。

## 1 自有库核对（按机主指向）

| 项 | 实读 |
|---|---|
| 上游 | `KIntegrated/vllm-gfx906-mobydick` |
| 我们的 fork | `phoenixclyde/vllm-gfx906-mobydick`（fork=True，size 287,697 KB，pushed 2026-10-06T15:38:33Z） |
| 分支 | `gfx906-patches` · `gfx906-patches-030` · `gfx906-patches-030-autogptq` · `gfx906-patches-030-e2packed` · `gfx906/v0.30.0` · `main`（**tag 空**） |
| 我们的技能 | `.agents/skills/gfx906-isa-disassembly` · `gfx906-mem-attribution` · `gfx906-rocprofv3-kernel-trace` |
| gfx906 内核源 | `csrc/rocm/{moe_q_gemm_gfx906.cu, dense_gemv_gfx906.cu, moe_align_m1_gfx906.cu, moe_q_gemm_rdna3.cu}` · `csrc/gfx906_fa/**` · `csrc/libtorch_stable/gdn/fused_gdn_decode_kernel.cu` |
| gfx906 专用 MoE 调参 | `vllm/model_executor/layers/fused_moe/configs/E=128,N=192,device_name=AMD_GFX906,dtype=int8_w8a16.json` |
| ISA 探针 | `benchmarks/kernels/gfx906/dot_isa_probe.py` · `docs/gfx906/dequant-instructions.md` |

**更正一条我此前的说法**：W737 我写「routeK 树里没有这些内核」是**对着 routeK 的本地树**说的，
成立；但**源在自有 GitHub 库里有**（上述路径），机主指正正确。-> 新铁律：
**引用 routeK 的内核结论，先读自有库的对应分支；本地树只是它的一个工作副本。**

## 2 R1 交付：`deploy/tools/isa_probe.py`

移植自上面那份技能，并做了三处适配（都是实测撞出来的）：

1. **可执行文件不能只靠 bundler**：对**链接后的 `strata`**，`clang-offload-bundler -unbundle`
   **只吐 1 个成员**（7,888 B），而 `.hip_fatbin`（15,606,216 B）里实际有 **59 个设备 ELF**。
   技能假设的是每个 `.hip.o`（含自己的 `.hip_fatbin`），而 `build-906` 里 **`.hip.o` 计数 = 0**。
   -> 规则改为：**可执行文件先按 ELF 头雕取**（e_shoff + e_shnum*e_shentsize），bundler 只用于 `-list` 校验三元组。
2. **溯源内建**：产出 `isa_provenance.txt`（binary / md5 / size / mtime / bundle targets）。
3. **全量普查内建**：产出 `isa_census.txt`（59 个对象的**全量**助记符计数），不只 top-N。

另外记录两个**计数陷阱**（技能里已写，我复现了）：
地址是 **14 位十六进制**（用 `[0-9a-f]{8}` 会静默匹配 0 行）；
助记符在**行首**、地址/编码在 `//` 注释里（我第一版正则按「地址在行首」写，直方图全 0）。

## 3 R2 结论：Strata 的 IQ4 走 dp4a + 解包，**全树 0 条 dot8**

**溯源**（按技能铁律）：`/src/build-906/strata` · md5 `160611838796d4b172ec3a642ccd988d` ·
24,982,264 B · mtime `2026-10-08 14:14:35 +0000` · bundle target `hipv4-amdgcn-amd-amdhsa--gfx906`。

**全二进制 ISA 普查（59 个设备 ELF / 1,926,163 条指令）**：

| 指令 | 计数 | 说明 |
|---|---|---|
| `v_dot4_i32_i8` | **62,596** | 唯一在用的整数 dot（= `dp4a`） |
| `v_dot8_i32_i4` | **0** | 原生 packed nibble，**未使用** |
| `v_dot2_f32_f16` | **0** | fp16 dot2，**未使用** |
| `v_pk_fma_f16` | **0** | 打包 fp16 FMA，**未使用** |
| `v_mfma_f32_16x16x16f16` | **0** | gfx906 无 MFMA |
| `v_perm_b32` | 10,403 | 解包帮手 |
| `v_and_b32_e32` | 37,655 | 解包 |
| `v_lshrrev_b32_e32` | 16,661 | 解包 |
| `v_lshlrev_b32_e32` | 26,870 | 解包 |
| `v_bfe_u32` | 5,130 | 解包 |

**逐内核（focus = IQ4/IQ3 家族）**：

| 家族 | 内核数 | 总指令 | dot4 | 位/解包 |
|---|---|---|---|---|
| `native_mmvq_*<IQ4XSTraits,...>` | 40 | 23,406 | 2,384 | 1,536 |
| `native_mmvq_*<IQ4NLBlock,4>,...>` | 42 | 19,680 | 1,212 | 795 |
| 泛型 `mmvq_multi_kernel<typeID>` | 2 | 887 | 40 | 128 |

例：`native_mmvq_wave_kernel<IQ4XSTraits,8,1>` = 558 条指令里 **64 条 dot4 + 158 条位操作**
（`v_perm_b32` 等），即 **约 2.5 条位操作喂 1 条 dot**。源码 `iq_kernels.cu` 里
`vec_dot_q5_1_q8_1`（:502-519）、`vec_dot_q6_K_q8_1`（:531-539，用 `STRATA_DP4A`）与之一致。

**ISA 可编码性探针（含反例，全过）**：

| 指令 | 结果 | 编码 |
|---|---|---|
| `v_dot8_i32_i4` | **支持** | `[0x00,0x40,0xaa,0xd3,0x01,0x05,0x0e,0x1c]` |
| `v_dot4_i32_i8` | 支持 | `[0x00,0x40,0xa8,0xd3,...]` |
| `v_dot2_f32_f16` | 支持（4 操作数） | `[0x00,0x40,0xa3,0xd3,...]` |
| `v_mfma_f32_16x16x16f16` | **如期被拒**（`not supported on this GPU (gfx906)`） | 反例成立，探针非空 |

-> **判据**：Strata 的 IQ4 正落在 routeK 速率表里**最慢的那一格**（i4 解包 + dot4 = 1,375 GMAC/s，
0.24x fp32），而原生 nibble 的 `v_dot8_i32_i4` = 49,600（8.52x fp32）。
但 routeK 已把话说死：**「requires i4 data on BOTH operands, a Q4 format change, not an instruction swap」**
-> 我们激活是 int8（q8_1），**换 dot8 等于换权重格式 + 换激活格式**，不是改一条指令。
**本轮结论：不改（P38 = REJECTED）。**

## 4 R3 结果：MTP **有效接受长度 ≈ 1.79**，低于 2.0 门槛

口径：**引擎自报**（stderr 摘要 + `/metrics` 的 `drafts_accepted/drafts_offered` 两侧一致）。

| 请求 | 生成 | 草稿 offered / accepted | 步数（生成-接受） | 有效接受长度 |
|---|---|---|---|---|
| 1（冷） | 700 | 413 / 312 | 388 | **1.804** |
| 2（温） | 700 | 428 / 309 | 391 | **1.790** |
| 合计 | 1,400 | **841 / 621** | 779 | **1.797** |

- **接受率 = 621/841 = 0.738**（`/metrics` 的 delta 也是 841/621，两口径逐位一致）。
- 引擎 banner：`strata verify: window up to 6 tokens`；实采窗口会**自适应**
  （日志逐字 `capturing the 1/2/3/4/6-token window`），实测每步只 offer **约 1.06 条**草稿
  -> 有效窗口约 2。
- 旁路：`suffix drafts: 22 windows, 45 of 66` / `9 windows, 26 of 29`。
- 源码自己的先验是 **0.86 per draft**（`src/spec/controller.cpp:21`，flyweight 在该模型上测的）
  -> **我们实测 0.738，比先验低 0.12**。

-> **判据**：R5（`--mtp-q4`）的门槛是「R3 过 2.0」。实测 **1.797 < 2.0** -> **门槛未达，R5 关闭**
（`--mtp-q4` 不值得开）。旁证：源码注释 `draft_policy.cpp:57` 的 `1.0 + 0.7*(t-1)`、
以及窗口被自适应压到 ~2 这一现象，都指向同一件事：**这批专家的草稿在位置 2 之后就不值钱了**。

## 5 对候选表的修订（W737 §8）

| 原序 | 项 | 本轮 |
|---|---|---|
| R0a | `EXPERT_V2` | W739 已做，REJECTED |
| R0b | `TSUM` | W739 已做，REJECTED |
| **R1** | ISA 反汇编规程 | **已完成**：`deploy/tools/isa_probe.py`（含溯源 + 全量普查 + 两个实测陷阱） |
| **R2** | IQ4 内环 objdump | **已完成**：dot4 = 62,596 / dot8 = 0；dot8 需双方 i4 -> **不改** |
| **R3** | 接受长度 | **已完成**：有效 1.797（<2.0） |
| R4 | `--kv` 四档质量门 | 未做（KLD 主门需先建 harness） |
| R5 | `--mtp-q4` | **关闭**（R3 未过 2.0） |
| R6 | `--lookup-chain` | 未做（低期望） |
| R0c | `LFUSE`/`GROUPED_V1`/`SH_STREAM` | 未做（须串行） |
| R7 | 布局押预填 | 未做 |
| R8 | 单卡读数贡献上游 | 未做 |

## 6 落盘

- **新建** `deploy/tools/isa_probe.py`（R1 交付；bundler + 溯源 + 全量普查；三处实测适配）
- **新建** `deploy/W740_ISA_PROBE.md`（本文）
- 证据：`deploy/tmp/_w740_isa_mc.txt` · `_w740_isa_symbols.txt` · `_w740_isa_focus.txt`（4.1 MB） ·
  `_w740_isa_census.txt` · `_w740b_isa_{hist,mc}.txt` · `_w740d_isa_{provenance,census,mc}.txt` ·
  `_w740_r3_result.json` · `_w740_ki_isa_skill.md`（自有库技能全文）· `_w740_tree_gfx906-patches-030.txt`
- 166：`/home/albus/strata166/_w740/isa_probe.py`；容器 `/tmp/isaprobe{,2,3,4}/`
- `PARAM_REGISTER.tsv`：P38 / P39（见 register）
- `MEMORY.md`（走技能）与本日志

**未动生产**：`-407` Up、HTTP 200、serve 覆写 2 未受影响；166 只读 + 只建 `_w740/` 目录。
- **例外**：`deploy/tmp/_w740_ki_isa_skill.md` 是从自有库逐字取回的技能原文，含上游自带的 U+2014/U+00D7，**按 upstream 件先例不重写**（同 W734 对上游 `app.js` 的处理）。


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `957a9696940102a678e5de6e5e67f0c9`（字节 10411）。
