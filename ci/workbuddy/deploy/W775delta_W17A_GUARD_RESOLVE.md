# W775delta W17a 补完 ---- 20 条「有守卫」全部读到源码级判据

日期 2026-10-11 ｜ 源 = 本机 0.1.42 源码树 `deploy/tmp/src142/`（机主指出源码在 166 镜像里，已归档）｜ **0 发车**

## 0 本件补的是什么

`W775delta_W17A_GUARD_TRIAGE.md` 把 205 条（132 X + 73 M）分了桶，但留了 **20 条判不动的**
（列 G 写着「有守卫（原文见列 G）」，并注明**发车前不能用**）。本件用新归档的 0.1.42 源码树**逐条读守卫上下文**，把它们全部解析掉。

## 1 意外收获：上游自带的「改答案开关」**权威名单**

`include/strata/core/arch_defaults.hpp:7-8` 逐字：

> `// Switches that change bits (STRATA_PF_GEMM, STRATA_PF_FUSED, STRATA_HC_UPMIX, STRATA_PA_FAST, STRATA_HIP_WMMA,`
> `// STRATA_SELECT_WMMA, STRATA_HC_Q8: rounding-level, KL-gated) stay opt-in; docs/STRIX_HALO.md lists them.`

`src/core/arch_defaults_test.cpp:42` 又补两个（同一 CHECK 名单）：

> `{"STRATA_PF_GEMM", "STRATA_PF_FUSED", "STRATA_HC_UPMIX", "STRATA_PA_FAST", "STRATA_HIP_WMMA",`
> ` "STRATA_SELECT_WMMA", "STRATA_HC_Q8", "STRATA_PF_HCDOWN", "STRATA_WMMA_GEMM"}`

=> **权威「改答案」名单 = 9 条**：`PF_GEMM` · `PF_FUSED` · `HC_UPMIX` · `PA_FAST` · `HIP_WMMA` · `SELECT_WMMA` · `HC_Q8` · `PF_HCDOWN` · `WMMA_GEMM`。
**这比我上一轮按名字猜的启发式可靠得多**，已作为 `W17b` 发车前的硬判据。

同头文件 `:3-6` 另有两条对我们**极重要**的声明（逐字）：

> `// Every gfx1151 ... switch in the table was measured on Aurora ... with BYTE-IDENTICAL output against the same engine with`
> `// the switch off: the same token ids at 4K / 32K / 64K and on four models, and a bitwise harness per kernel.`
> `// They are therefore on by default on that architecture and nowhere else: a CUDA build and every other HIP architecture`
> `// run the code they always ran.`

=> **该表全部是 gfx1151/Aurora 的数、且"on by default 只在该架构"**，与我们 R4 的结论一致（gfx906 取空表）。

## 2 20 条逐条解析（源码级）

| 名 | 桶 | 守卫（原文） | 运行期门 ---- 依据 | 改答案 |
|---|---|---|---|---|
| `STRATA_DENSE_MMQ` | X | `#if defined(STRATA_PREFILL_MMQ) && defined(__HIPCC__)` | **可达**（字符串在二进制 => 该 CMake 选项已开）；须 `=1` **且** `mmq::built()` **且** `mmq::fits(type,N)` **且** `K%256==0`（`prefill/gemm.cu:736-745`） | **嫌疑**（整数 MMQ 核） |
| `STRATA_EXP_MODE` | X | `#if STRATA_EXP_LAYOUTS` | **可达**：`iq_kernels.cu:2818` `#if defined(STRATA_HIP_GFX906) \|\| !defined(__HIPCC__)` => 本构建 `STRATA_EXP_LAYOUTS=1`；gfx906 默认 `kExpModeDefault=7`（`:2824`） | 待判（改专家布局模式） |
| `STRATA_GDN_NOY` | X | `#if defined(__HIPCC__)` | **arch_defaults 表项**（`:45`）=> gfx906 **不自动设**、须显式 | 待判（表头称 gfx1151/Aurora 上 byte-identical） |
| `STRATA_GDN_PP` | X | 同上 | 表项（`:39`；注释 *two columns per lane: 64K prompt +2.9%*） | 同左 |
| `STRATA_HIP_PROMPT_F16` | X | `#if defined(__HIPCC__)` | 可达（须 `=1`）；`gemm.cu:359-364` 逐字 *"It changes the prompt path's numbers (an FP16 rounding of each 16-bit GEMM's output), so no card gets it unasked"*；收益在 **gfx103x** | **改答案（上游逐字）** |
| `STRATA_IO_PF_AHEAD` | X | `#if defined(__linux__)` | 可达（`expert_source.cpp:623`）；属 `IO_PREFETCH` 族（`P54 REJECTED`：大 RAM 下 0 预取） | 否 |
| `STRATA_IO_PF_STAGE` | X | `#if defined(__linux__)` | 可达；`generate.cpp:4572` 逐字 *"measured faster only on a 32 GB-class box (+25% on an RTX 3060, 32 GB); it was slower at 16 GB and on an iGPU"* | 否 |
| `STRATA_NORM_ROPE` | X | `#if defined(__HIPCC__)` | 可达（须 `=1`）；`native_rope.cu:186` 逐字 *"AMD: opt in until rope_parity check 6 passes there"*；须 `head_dim in {128,256}` 且 `n_rot==64` | **嫌疑高（parity 未过）** |
| `STRATA_NO_LARGEPAGES` | X | `_WIN32` **+ Linux 分支** | **可达**：`pinned.cu:203-206` 逐字 *"the same-run A/B switch the Windows branch documents; honor it"*；另 `:257/:264` Linux 路径亦读它 | 否（只影响页粒度） |
| `STRATA_PF_GEMM` | X | `#ifdef STRATA_USE_HIP` | 可达（`=1`，`prefill/gemm.cu:682/826`） | **改答案（权威名单）** |
| `STRATA_PF_OCC` | X | `#if defined(__HIPCC__)` | 可达（`=N`）；`prefill/moe_fused.cu:589` 逐字 *"the same work items and arithmetic: **the results do not change**"* | 否 |
| `STRATA_PF_OCC_W` | X | `#if defined(__HIPCC__)` | 可达（`=N`，`moe_fused_iq.cu:1009`）；同族 | 否 |
| `STRATA_PF_PAD` | X | `#ifdef STRATA_USE_HIP` | 可达；`gemm.cu:822` 逐字 *"**Bitwise the same products**"*；**须 `PF_GEMM=1`** 且 `T>=pf_min_t` / `T>=64` / `N>=512` / `K%32==0`（`:828`） | 否（**但必须搭改答案开关 `PF_GEMM` 才生效**） |
| `STRATA_READ_AHEAD` | X | Linux 分支（`else`） | 可达；`platform/memory.cpp:152` **默认开**（`v==nullptr \|\| atoi(v)!=0`），`=0` 关 | 否 |
| `STRATA_SELECT_WMMA` | X | `#if defined(__HIPCC__)` | 可达（`=1`，`qsa_select.cu:1126` 注释 *"the **gfx12 (RDNA4)** WMMA scorer, opt-in"*）=> **机制是 RDNA4 WMMA** => 本卡（gfx906 无 WMMA）**预期不兑现** | **改答案（权威名单）** |
| `STRATA_SESSION_BUFFERED` | X | Linux 分支 | 可达（`conversation_file.cpp:340`，`=1` 强制缓冲 IO） | 否（自检件注释 *"writes and reads the same bytes"*） |
| `STRATA_UNBUFFERED_LOAD` | X | `#if defined(_WIN32) \|\| defined(__linux__)` | 可达（`expert_source.cpp:471/1618`；设值即强制） | 否 |
| `STRATA_VERIFY_NODES` | X | `#if !defined(STRATA_USE_HIP)   // a CUDA debug listing` | **本卡走该分支**（主引擎不定义 `STRATA_USE_HIP`，与 `ROUTE_TAIL_SKIP` 同型）=> 可达；但它是**调试列举**（`verify.cpp:1769` 用 `cudaGraphGetNodes` 打印节点类型） | 否（只诊断） |
| `STRATA_NO_ARENA_THP` | M | Linux 分支（`else`） | **可达**（`pinned.cu:256`：跳过 transparent huge page 请求） | 否 |
| `STRATA_PIN_GUARD` | M | `#if defined(__linux__)` | **可达**（`expert_source.cpp:2758`；`=2` 分步 page-lock 补集） | 否 |

## 3 短名单更新（相对 `W17A_GUARD_TRIAGE.md` §4）

**新增 9 条**（可达 + 不改答案 + 有族/机制线索）：
`PF_OCC` · `PF_OCC_W`（prefill，上游注释"结果不变"）· `IO_PF_AHEAD` · `IO_PF_STAGE` · `READ_AHEAD`（KV/IO）·
`SESSION_BUFFERED`（会话）· `NO_ARENA_THP` · `PIN_GUARD`（M 桶但**单卡仍活**，正是 `W17c` 要的样本）· `UNBUFFERED_LOAD`

**移出 1 条**：`SELECT_WMMA` ---- 进短名单时是"待判"，现据权威名单判**改答案** + 机制为 RDNA4 WMMA（本卡不兑现）=> **不发车**。

**降级 1 条**：`PF_PAD` ---- 本身不改答案（*Bitwise the same products*），但**必须搭 `PF_GEMM=1`**（改答案开关）；
=> 不能单独发车，须作为 `PF_GEMM` 车的**附带读数**。

=> 短名单：**36 -> 44 条**（+9 / -1 / 降级 1）。

## 4 方法学保值：`strings` 硬规则经一次反例排查后**成立**

`STRATA_NO_LARGEPAGES` 起初像"假阳性"（我读到的第一段在 `#ifdef _WIN32` 里），若为真则会**推翻** `W17` 的
「二进制字符串命中 = 编进本机镜像」硬规则。**回源码全库 grep（10 处命中）后判定：不是假阳性** ----
`src/core/pinned.cu:203-206` 在 **Linux 路径**上另有同一 env 的读取（逐字 *"the same-run A/B switch the Windows branch
documents; honor it"*），`:257/:264` 亦然。=> **该规则保持成立**（本条记为标准反例排查，供下次同类质疑复用）。

## 5 局限（必须随行）

1. 运行期门是**读源码 + 守卫文本**的判读，**不是跑出来的**；"可达"只表示**路径能走到**，不表示**有收益**。
2. 「改答案」分三档：**权威名单 9 条**（上游逐字）> **上游注释自认**（`HIP_PROMPT_F16` / `NORM_ROPE`）> **待判**（未声明）。发车前改答案类一律配 `STRATA_LOGPOS` 门（`P51`）。
3. `STRATA_DENSE_MMQ` 的"可达"依赖「字符串在二进制 => CMake 选项已开」这一步推断（与 `W17` 同一判据）；**未直接读本机构建缓存**。
4. 本件**未**逐条读 `STRATA_EXP_MODE` 各 mode 的数值后果（只读了默认值 7）。

## 6 产物

- 解析脚本 `deploy/tmp/_w17a_resolve.py`；事实核验 `deploy/tmp/_w17a_facts.py`
- 原始上下文 `deploy/tmp/_w17a_resolve.out.txt`（512 行）· `_w17a_facts.out.txt`
- 源码树 `deploy/tmp/src142/`（见 `W775delta_SRC142_VERIFY.md`）
