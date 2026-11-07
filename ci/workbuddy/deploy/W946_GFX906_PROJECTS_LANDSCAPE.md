# W946 · gfx906 项目全景（8 家）—— 同模型同卡的那家把 prefill 从 796 做到 1561

> **【AUDIT24 P1 · 2026-11-04】两处更正**：
> ①§6「prefill 796 → 1251（8K）/ 1561（32K）」**混了两个基线**。README 原文：**796 是"一 slot 的起点"**，
> 而 1251/1561/1977 的对照列是**同一服务配置的上一个默认分支 887/867/877** ⇒ 正确写法
> **887→1251、867→1561、877→1978**，796 只能单独当"起点"讲（+57% 是错的，实际 +41%/+80%/+126%）。
> ③**R89 的结论也撤**：本件 §6 表与 §7 仍写「当场判否（A 级源码）」「早已 gather-only」，但源码阅读按 `W939 §0` 是 **D 级**；`W947` 已把 `R89` 改回 **OPEN**（`W832@f40c8f39:803` 同步），待 depth 1×/3×/6× 实测。
> ②§56-63「我们 0.4.1 vs 社区 v0.7.0、差 3 个 minor」的判据已在 `W948` 自查中作废（版本号不是可比锚点），
> 见 `R90`。**【W953 更正】**版本号是**可用**的锚点（`LLAMA_VERSION` 就在我们自己 CMakeLists 里）：
> 本件当时写的「社区 v0.7.0」在今天是 **0.8.0**（`b12099`），我们仍是 **0.4.1** ⇒ 差 4 个 minor。
> 上一轮 `W948` 说「版本号不可比」、`AUDIT24` 跟着写「get_J_max 是自家补丁」，两条都已作废，见 `W953`。

- 日期：2026-11-04 15:3x–16:0x
- 触发：机主「你只找了一个项目吗？还有呢，尤其是相对比较新、跟 llama.cpp 上游比较紧的项目。」
- 结论先行：**找到了同模型（Qwen3.8-Flash-Next 177B MoE / UD-Q4_K_XL）、同卡（MI50）、同单流场景的那一家** ——
  `sixvolts/llamacpp-gfx906-furnace`，它把 **prefill 796 → 1251（8K）/ 1561（32K）/ 1977（pp8192）t/s**，
  而且每一条手段都能对上我们的相位表。**我们的 llama.cpp 是 0.4.1，社区最新已经到 v0.7.0（差 3 个 minor）。**

---

## 1 全景（按"离我们最近"排序，不是按星数）

| 项目 | 基线（上游） | 最新推送 | 核心手段 | 对**我们形状**的数字 |
|---|---|---|---|---|
| **sixvolts/llamacpp-gfx906-furnace** | upstream `e6ab7c1a4`（2026-09-22） | **2026-11-02** | 三平面 K-quant repack（Q4_K/Q5_K/Q6_K + **Q5_1/Q8_0 opt-in**）、异步分阶段拷贝、QSA 稀疏 prefill、GDN LDS 常驻、DPP 归约、MoE 16-token tile GEMM | **同模型 4×MI50：prefill 8K 887→1251、32K 867→1561、pp8192 877→1978**；单 MI50 27B UD-Q4_K_XL pp512 **216→325（+50%）** |
| **exabit-io/mx-llama.cpp** | merges **llama.cpp v0.7.0**（2026-10-22） | 2026-10-22 | mxxm-t 的 gfx906 fork + 九补丁（16 列扩展、Q8_0 快速路径、单列整块加载、两个内核折叠、DPP） | 四 die Qwen3.8-27B Q8_0：prefill +33%；单 die 1253 t/s（离线短 prompt） |
| **mxxm-t/mx-llama.cpp**（原 mixa3607） | upstream `b11553` | 活跃 | weight repack（Q8_0/MXFP4/K-quant/Q5_1）、q8_1 激活复用、BF16→F32、tile 选择 | **本模型 43 个 Q5_1 tensor：+11% prefill（四卡）**；Q5_1 +84%（单卡 dense） |
| **mixa3607/ML-gfx906** | 打包器（含 **Strata** 子项目） | 2026-10-31 | 构建镜像；**Strata 与 llama.cpp 两个构建都用 `-mllvm -amdgpu-sched-strategy=max-ilp`** | —（构建口径，不是算法） |
| milpster/gfx906-llama-cpp | upstream `7887b88`（2026-09-24） | 2026-09-30 | 内层循环/tile、fattn | 41% issue ceiling 结构性；四家族全回归 |
| iacopPBK/llama.cpp-gfx906 | build **7924**（旧，已迁 mx） | — | gfx906 kernel 目录 | `#21698` 的 +28~36% 在 vega 表上实测 **+1.0%** |
| exabit-io/llama.cpp-gfx906-tuning | 4×Vega II 调优指南 | 2026-10-23 | 参数矩阵、功率-吞吐、KV 类型 | 单 die prefill 1130、离线 1253；**KV f16 最快 decode** |
| Kausik-A/gemma4-mi50-optimizations | — | 2026-08-02 | **Q8_1 reuse + fused QKV** | 对应我们的 R87（待读源码） |

## 2 furnace 逐项对照我们的相位表（这是本轮最该看的东西）

它针对的模型、量化、卡数、单流场景**与我们完全相同**（177B MoE / UD-Q4_K_XL / 4×MI50 / 单流），
README 还给了每个改动的 A/B。逐条映射到我们的指标：

| furnace 的手段 | 它的数字 | 我们的对应事实 | 判断 |
|---|---|---|---|
| **异步分阶段图输入拷贝**（pinned per-copy-slot） | **pp8192 877 → 1978 t/s（+126%）** | 我们 `wait copy` 相位占 prefill **8.9–12.7%**（AUDIT16 rep0）；专家 blob 也是 PCIe 上传 | **最大单项，我们完全没有对应条目** |
| **QSA prompt attention 只读被选中的 key**（context ≥ 3× selection 时） | **pp4096 @48K depth 622 → 1150（+85%）** | `W926` 实测我们的 attn 指数 1.20（已稀疏），但**每 token 仍读 2048 cell**；`W887` 有效算力 11–16% 峰 | **R85/R46 的最强外证** |
| **三平面 K-quant repack**（含 MoE 专家栈） | 单 MI50 27B UD-Q4_K_XL pp512 **216→325（+50%）**；"on-disk superblock 布局把 GCN matvec 压到 **58% HBM**，repack 后 **89%**" | 我们 Q5_1 down 供给率 **25% 峰**、Q4_K gate/up 30–35%；`MemUnitStalled 0.36%` | **R86 的直接支持**，且它证明 **Q4_K 也值得 repack**（mx 说 Q4_K 只 +2~5%，furnace 说 +50% —— 见 §3） |
| **GDN LDS-resident prefill** | 含在 1251 里 | 我们 `R54` 判否（megakernel 在 T≥4 才赢）；但它是"LDS 常驻"不是 megakernel | 需重看，**R54 的结论不能覆盖这条** |
| **QSA indexer key pooling + block scoring 融合内核** | 含在 1251 里 | 我们 `qsa select` 仅 0.5%（`W926`） | 我们这块已经很小，优先级低 |
| **DPP/ds_swizzle warp 归约** | backend-wide | 我们 `R55`（101 处 `__shfl*`，DPP 仅 4 处） | 低风险、可量化 |
| **MoE grouped 16-token-tile GEMM** | 含在 1251 里 | 我们 `moe_mmq_tab` J=64、每专家 ~320 token | 需对照它的 tile 选择 |
| **自适应 MTP**（`--spec-draft-max-slots`） | 6 用户 decode 57→98 | 我们单流，不适用 | 跳过 |

**一句话**：它把 prefill 从 796 提到 1251（8K），归因里**最大的一块是我们连条目都没有的"拷贝/调度"**，第二是 **QSA 稀疏 prefill**，第三才是 repack。

## 3 两个矛盾必须写清（不许含糊）

**矛盾 A：Q4_K repack 到底是 +2~5% 还是 +50%？**
- mx 的表格：Q4_K_M **+2%（1 GPU）/ +5%（2 GPU tensor）**；
- furnace：单 MI50 Qwen3.8-27B UD-Q4_K_XL pp512 **216 → 325（+50%）**，但那是**全类型组合**（Q4_K+Q5_K+Q6_K 都开），不是 Q4_K 单独。
⇒ 合理读法：**furnace 的 +50% 是"全类型三平面"合计**，Q4_K 单项可能仍是几个百分点；我们的 gate/up 全是 Q4_K（47 层），所以**真正的大头还是 down 的 Q5_1**（88.6% 字节）。
⇒ 但也要注意：furnace 明确说它的 repack 是**三平面**且针对 **MoE 专家栈**，mx 的 Q4_K 是"de-aliased nibbles + scale/min record"两平面 —— **两者的 Q4_K 实现不同**，不能用一个的数字否另一个。

**矛盾 B：MMQ 到底是不是访存受限？**
- 我们 PMC：`MemUnitStalled 0.36%` ⇒ 不是；
- furnace："on-disk superblock 布局把 GCN matvec 压到 58% HBM，repack 后 89%" ⇒ 是。
⇒ 两者都对，但**对象不同**：我们测的是 **prefill 的 MMQ（M=320/专家，算术密集）**，它说的是 **decode 的 matvec（M=1，纯带宽）**。
⇒ **结论：repack 在 prefill 上的收益不能按 58%→89% 推**，必须自己 A/B（这正是 `W945 §6` 的判据）。

## 4 版本差：我们的 llama.cpp 是 0.4.1，社区是 v0.7.0

- 我们：`~/strata166/llama.cpp` 的 `LLAMA_VERSION 0.4.1`（含 `#27841` 的 GCN config，故 ≥ 2026-09-12）；
- exabit：merge **llama.cpp v0.7.0**（`620d222`，2026-10-22）；
- furnace：upstream `e6ab7c1a4`（2026-09-22），并在其上叠 qwen4exp/MTP。

⇒ 我们与社区最新**差 3 个 minor 版本**。这不必然带来性能差（我们的 MMQ 是自研 tab 路径），但它意味着
**上游这三个月里对 qwen4exp / GDN / QSA 的修正我们一条都没吃到** —— 而 furnace 正是在这三个月里把同模型 prefill 翻了一倍。

## 5 重评：上一轮把权重放反了

| 层 | 上一轮权重 | 本轮修正 | 依据 |
|---|---|---|---|
| 指令层（tile / 内层循环 / dot 指令） | 最高（R51/R58/R60/R63/R84 全查） | **最低**（已全关，且三家外证一致：结构性） | milpster 四家族回归、mx 不做 dot8、furnace 也不做 |
| **布局层（weight repack）** | 上一轮补上（R86），但只当"Q5_1 一个小项" | **高**：三家都做，furnace 把它算进 +50% 组合 | mx/furnace/exabit |
| **拷贝/调度层** | **完全缺失** | **最高**：furnace 单这一项 +126%（pp8192） | furnace README |
| 算法层（QSA 稀疏 prefill / GDN LDS） | 中（R46/R54） | **高**：+85%（48K depth） | furnace |

## 6 新条目（本轮立，按证据强度排序）

| id | 内容 | 外证 | 第一步 |
|---|---|---|---|
| **R88** | **prompt 路径的异步分阶段拷贝**：把"专家 blob / 图输入"的 host-sync 拷贝改成 pinned per-slot 异步，消除 ubatch 间的设备排空 | furnace **pp8192 877→1978（+126%）** | 先量：我们 prefill 的 `wait copy` 绝对 ms 与每次 ubatch 的同步点（日志已有相位） |
| **R89** | **QSA prompt attention 只读选中 key** | furnace **pp4096@48K 622→1150（+85%）** | **当场判否（A 级源码）**：`qsa_prompt_attn.cu:120-200` 的 `n = steps[qi*kStepCount + kStepWidth]`、`ids += qi*cap`、主循环 `cell = ids[c0+c]` 经 `page_table` 映射 ⇒ **我们早已是 gather-only**。详见 §7 |
| **R86**（已有） | Q5_1（+ 视结果扩到 Q4_K）repack | mx +11% 本模型、furnace 组合 +50% | `kq_bench` 两臂 A/B（`W945 §6`） |
| **R87**（已有） | q8_1 激活复用 | mx +2.2~2.6% | 先量每请求量化时间 |
| **R49**（已有） | `-mllvm -amdgpu-sched-strategy=max-ilp` | **mixa 的 Strata 与 llama.cpp 两套构建都默认加** | 我们已有开关验证过改汇编 66 行，直接 A/B |

## 7 下一轮源码待读（已排）

0. **`qsa_prompt_attn.cu` 已读**（本轮，R89 判否）：`prompt_attn_kernel` 第 131 行 `n = steps[qi*kStepCount + kStepWidth]`（选中 cell 数）、
   第 133 行 `ids += qi*cap`（选中列表）、第 193 行 `for (c0 = 0; c0 < n; c0 += CH)` 内 `cell = ids[c0+c]` 经 `page_table` 映射。
   ⇒ **我们已经是 gather-only**，furnace 的 +85% 对我们不成立；`W926` 的 1.20 指数 = indexer 的 O(n) + core 的 O(2048) 混合。
   剩下只有 R46 的**效率**（1.5–2.1 TFLOPS = FP32 峰 11–16%）。
1. `sixvolts/llamacpp-gfx906-furnace` 的 repack trait（三平面，MoE 专家栈）与 **异步拷贝补丁**（`LLAMA_ASYNC_INPUT_MIN_TOKENS`、`GGML_SCHED_INPUT_STAGE_MB` 附近）；
2. `Kausik-A/gemma4-mi50-optimizations` 的 Q8_1 reuse（对应 R87）。

## 8 方法教训

> 上一轮我按 "MMQ / gfx906 / prefill" 搜，找到的是**做 kernel 的人**；
> 这一轮按 **"我们模型的名字 + 我们的量化"** 搜（`Qwen3.8-Flash-Next` / `UD-Q4_K_XL` / `177B MoE`），
> 直接找到**做同一个模型的那家** —— 它给出的不是"某个 kernel 快多少"，而是**"整条 prefill 从 796 到 1561 的完整归因"**。
> **搜关键词要找"同题的人"，不是找"同领域的人"。**
