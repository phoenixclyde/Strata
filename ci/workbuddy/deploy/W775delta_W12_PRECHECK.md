# W775delta W12 -- 0.1.42 gfx906 四开关复测：**发车前源码核实**

> `W750_MASTER_PLAN.md` §1 W12 / `W713_PLAN.md §6.4 #9`（P1''）。
> 时间：2026-10-11 04:3x。本件**只做源码面核实 + 发车条件判定**，未发车（发车须停生产、须 5+ runs）。

## 0 结论（先行）

1. **四开关在 0.1.42 里全部在位**，且**全部是 HIP 侧 opt-in（默认关）**：
   `STRATA_GFX906_ATTN_QUERY_SWIZZLE`(=1) · `STRATA_GFX906_ATTN_REDUCE12`(=1) · `STRATA_HEAD_MIX_MULTI`(=1) · `STRATA_ONE_TOKEN_COMMIT`(=1)。
2. **W774「prefill 全中性」的原因找到了** -- **不是"开关无效"，而是"开关不作用于 prefill"**：
   swizzle 路径**只在 `n_q=1`（decode）+ `kv_mode == 1`（INT8/k8v4）+ 非 lane_cell 时选中**；
   `HEAD_MIX_MULTI` / `ONE_TOKEN_COMMIT` 作用于 **verify/commit 图**，也是 decode/MTP 面。
   => **拿 prefill 判它们＝拿错靶**。W774 的"中性"是**靶选错**，不是结论。
3. **臂序约束修正**：`P55`(swizzle) 与 `P56`(reduce12) **不是互斥的两臂** -- 源码里
   `REDUCE12` 是 `use_query_swizzle` 为真**之后的第二个更窄的分支**（`if (reduce12) ... else ...`）
   => **`P56` 必须在 `P55` 为真的前提下测**（原 W750 记的"P56 依赖 P55"**正确**，但原因要改写成这条）。
4. **`P59`/`P60` 同样必须同臂**（同一 `verify.cpp` 双开关，且 HIP 侧都是 opt-in）。
5. **发车口径必须改**：主口径从 **prefill ms** 改为 **decode ms/step**（n_q=1 步时），
   且**必须 `--kv k8v4`**（否则 `kv_mode != 1`，swizzle 恒不选中 => 测了个空）。

## 1 四开关源码定位（逐字）

| 开关 | 位置 | 默认 | 生效条件 |
|---|---|---|---|
| `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | `src/kernels/cuda/qsa_decode_attn.cu:641` | **HIP 默认关**（`v && v[0]=='1'`） | `query_swizzle && !lane_cell && kv_mode==1 && query_swizzle_gfx906_device()` |
| `STRATA_GFX906_ATTN_REDUCE12` | 同上 `:668` | 默认关（`v[0]=='1' && v[1]=='\0'`） | 需先 `use_query_swizzle` 为真 |
| `STRATA_HEAD_MIX_MULTI` | `src/core/verify.cpp:195` / `src/core/mtp.cpp:860` | **HIP opt-in (=1)**；CUDA 默认开 | decode/MTP verify 提交图 |
| `STRATA_ONE_TOKEN_COMMIT` | `src/core/verify.cpp:211` | **HIP opt-in (=1)**；CUDA 默认开 | 单 token 窗口的 self-commit |

**swizzle 块的编译守卫**（`:640`）：`#if defined(STRATA_HIP_GFX906)` -- **我们的构建有此宏**（实测 `-DSTRATA_HIP_GFX906` **26 处**、`-DSTRATA_USE_HIP` **0 处**）=> 代码**在二进制里**。 **更正（2026-10-11 12:1x，R4 step-2）：`STRATA_USE_HIP=1` **是定义的** ---- `src/cmake/hip_backend.cmake:89` 经 INTERFACE 目标 `target_compile_definitions(strata_hip_runtime INTERFACE STRATA_USE_HIP=1 ...)`；`CMakeLists.txt` 里不出现属正常。见 `deploy/W775delta_R4_P41_SCREEN.md` §2。**

**swizzle 的调用路径**（逐字注释）：
> `// Opt-in INT8 batched attention: prefill, verification and MTP (including n_q=1).`
> `// Other pool formats and lane-cell scoring keep their paths; qsa_decode_attn_step is unchanged.`
> `// A k8v4 model's MTP drafter uses INT8 pools and can therefore take this path.`

[!] 注意：注释写 *"prefill, verification and MTP"* -- 但**代码判据是 `kv_mode == 1` 且该 kernel 是 `attn_chunk_kernel`**，
prefill 走 `qsa_prompt_attn.cu`（**另一个文件**，`STRATA_PA_FAST` / `STRATA_PROMPT_ATTN_Q4` 等）=> **prefill 不经过这个 kernel**。
=> **注释的"prefill"指的是"verification 窗口的 n_q>1"，不是 prompt 阶段**。这正是 W774 打偏的根。

## 2 生产面现状（现取，作为臂内基线）

`/metrics`（`strata166-407` @0.1.42）：

| 键 | 值 | 对本车的意义 |
|---|---|---|
| `engine.kv` | **k8v4** | [OK] `kv_mode==1` => swizzle 可选中 |
| `engine.kv_resident` | 0 | -- |
| `engine.spec` / `mtp_max` / `lookup` | 6 / 4 / 3 | HEAD_MIX/ONE_TOKEN 作用于 MTP => 有靶 |
| `engine.expert_slots` | 9761 | -- |
| `engine.arena_mib` | 34245 | -- |

引擎 environ（`/proc/12/environ`）：`STRATA_SRC=/src` + **`STRATA_PREFILL_CPU_SHARE=0`**（仅此两项）。

## 3 W12 臂设计（修正后）

**原设计**（W750 §2）：`p41 -> sw1 -> sw2` + `hm1` 共 5 臂。
**修正后**：

| 臂 | 内容 | env | 相对谁 |
|---|---|---|---|
| **A** | 基线 | `STRATA_PREFILL_CPU_SHARE=0` | -- |
| **B** | `P55` | `+ STRATA_GFX906_ATTN_QUERY_SWIZZLE=1` | vs A |
| **C** | `P55+P56` | `+ ..._REDUCE12=1` | **vs B**（依赖 B） |
| **D** | `P59+P60` | `+ STRATA_HEAD_MIX_MULTI=1 STRATA_ONE_TOKEN_COMMIT=1` | vs A |

**四臂足够**（原 5 臂里的 `p41` 基线在 0.1.42 内已无意义 -- §6.3 纪律：跨版本不可当基线）。

**主口径**：`ms/step`（decode，n_q=1），**必须同时带 hit 与 reused**（W744/W748/W773 三次踩）。
**正确性门**：必须核 **输出逐位相同**（上游逐字：*"bitwise the same sums"* / *"bit-identical scores"*）。
**runs**：**≥5 对交错**（W774 首轮 decode 臂内 spread 16-21%，3 对不够）。

**前置**：`STRATA_GFX906_ATTN_QUERY_SWIZZLE_TRACE=1` 可先做**一条零成本确认**（启动时打 `strata attn-query-swizzle: active=...` banner），
用来**在发车前就证明"这条路径确实被选中"** -- 避免又一次"测了个空"。**这条建议先做**。

### 3.1 四条件的**源码面闭合证明**（零 GPU，已完成）

`use_query_swizzle = query_swizzle && !lane_cell && kv_mode == 1 && query_swizzle_gfx906_device()`（`:643`）

| 条件 | 本机取值 | 判据来源 |
|---|---|---|
| `query_swizzle` | **真**（需显式 `=1`） | env opt-in |
| `!lane_cell` | **真**（`STRATA_ATTN_LANECELL` 未设） | env |
| `kv_mode == 1` | **真**（生产 `--kv k8v4`） | `/metrics` `engine.kv=k8v4` |
| `query_swizzle_gfx906_device()` | **真** | `:550-571` => `gfx_arch_is(gcnArchName,"gfx906") && warpSize==64`；本机 MI50 = gfx906 + wave64（`HSA_OVERRIDE_GFX_VERSION=9.0.6`） |

=> **四条全真，path 可达** -- 不需要起车就能确认靶正确。
`STRATA_GFX906_ATTN_QUERY_SWIZZLE_TRACE=1` 的 banner 降级为"发车时的运行期双保险"（可选，一行日志）。

## 4 建议次序

1. **[零发车] banner 确认**：起引擎（可在现有容器内加 `-e STRATA_GFX906_ATTN_QUERY_SWIZZLE=1 -e STRATA_GFX906_ATTN_QUERY_SWIZZLE_TRACE=1`），
   读 stderr 是否出现 `strata attn-query-swizzle: active=1 nq=1 ...`。
   - 若 `active=1` => 靶正确，按 §3 发四臂车。
   - 若 `active=0` => 先查 `kv_mode` / `lane_cell` / device，别发车。
2. **[发车] 四臂 x 5 runs x 交错**。
3. **[落账] 按结果改 `P55`/`P56`/`P59`/`P60` 四条。**

## 5 局限

- 本件**未发车**：结论限于**源码在性与生效条件**。
- `qsa_decode_attn` 在 `compile_commands.json` 里 **count=0** => 该 `.cu` 不在静态编译清单（疑 JIT / 单独 nvcc->hipcc 路径）；
  **但 `STRATA_HIP_GFX906` 全局定义 26 处** => 守卫通。**建议发车前用 banner 做一次运行期确认**（§4.1），不要只凭编译面。
- 上游 gfx906 社区报告（`bench/results/2026-10-08-gfx906-qsa-query-swizzle/`）声称**组件 +14.6% / 整模型 +1.185% prompt / −1.049% latency**，
  是 **2x Radeon Pro VII** -- **不是我们机型**，且其"prompt"口径与本机 prefill 定义**未必同**，须对齐后再比。


> **[BAN 归一说明 · 2026-10-11]** 本件属"活跃交付件"，已按项目禁用码位表（见 `W750_MASTER_PLAN.md` 第 0.5.7 节）做 **ASCII 归一**，映射：`U+2192`->`->` · `U+21D2`->`=>` · `U+2026`->`...` · `U+0394`->`delta` · `U+00D7`->`x` · `U+2014`->`--` · `U+2605`->`命中`/`*` · `U+2460-U+2469`->`(1)-(10)` · `U+2705`->`[OK]` · `U+26A0`->`[!]`。
> **引文处语义一字未改**，原文形态可回溯：改前副本 `deploy/tmp/_w21_bak/`（改前 md5 见件尾注）。
> 改前 md5 = `fbbac50e95e31ef4373c64792d742b13`（字节 7441）。
