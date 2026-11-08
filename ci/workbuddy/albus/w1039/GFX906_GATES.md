# gfx906 能力门清单（`R105` / `P479`）

> 立件原因：`--kv-grow` 的 VMM 门（`vmm.cpp:167`）是一条**撰写时的假设**，一秒探针就推翻了它（`P472`）。
> 同一形状的条件在本树里有 93 处。这张表把它们分成三类，只留「靠判据能翻案」的那部分去实测。
> 全部工作**零停机**：读码 + 独立 HIP 探针（几十 KB、1 秒 GPU、不启引擎）。

## 0 一条比 93 处更根本的事实：这棵树**不定义** `STRATA_USE_HIP`

```
$ grep -o "DSTRATA_USE_HIP[=0-9]*" build-masterp/build.ninja | sort | uniq -c
      1 DSTRATA_USE_HIP=1
$ grep -n -B1 "DSTRATA_USE_HIP=1" build-masterp/build.ninja | grep "build "
build CMakeFiles/strata_engine.dir/src/core/dflash2.cpp.o: ...
```

**全构建只有 `dflash2.cpp` 一个 TU 定义它**；其余（`vmm.cpp` / `mtp.cpp` / `verify.cpp` / `generate.cpp` / `prefill.cpp` …）都是 `-DSTRATA_HIP_GFX906=1` 而无 `-DSTRATA_USE_HIP`。

⇒ 这棵树是「HIP，但按 gfx906 兼容态编译」。后果：**任何写成 `#if defined(STRATA_USE_HIP)` 的功能在 gfx906 上都是死代码**，而写成 `STRATA_USE_HIP && !STRATA_HIP_GFX906` 的是**双死**——第一个合取项就已经为假，`!GFX906` 那半句在本构建里是冗余的。

这解释了一类现象：不是「gfx906 硬件少什么」，而是「构建开关没开」。要动它必须**逐块**，不能整体 `-DSTRATA_USE_HIP=1`（那会一次点亮几十条未知路径）。

## 1 「HIP 但排除 gfx906」七处，逐条判

| # | 位置 | 排除的功能 | 类别 | 判据 / 处置 |
|---|---|---|---|---|
| 1 | `core/vmm.cpp:158/167` | HIP 虚拟内存（弹性 K/V = `--kv-grow`） | **假设**（已推翻） | 探针实测属性 1、全周期正确 ⇒ 已改为 OR，候选 `kvg`（`P472`/`P474`） |
| 2 | `core/mtp.cpp:486` | MTP 草稿流放到**最高优先级**（`STRATA_MTP_HIP_PRIO`） | **可选开关被编译掉** | HIP 侧默认只对 gfx12 开（`gfx_arch_is_gfx12`），所以解开**不改默认行为**，只让 `STRATA_MTP_HIP_PRIO=1` 可用；外证：R9700 上 draft wall 5.8→3.5 ms/窗 |
| 3 | `core/verify.cpp:1213` | 拷贝流最高优先级（`STRATA_COPY_HIP_PRIO`，opt-in） | **可选开关被编译掉** | 同上，默认关；注释说共享队列时 `--pcie-mode dma` 会串行 |
| 4 | `program/generate.cpp:3078` | `prime_hw_queues()` 函数体 | **假设** | 函数自己的默认判据就是「gfx1200/1201 且 Linux」，解开不改默认；机制（loader 线程竞态开 HW 队列 ⇒ 一半启动把两条忙队列排到同一 pipe）**与卡无关** |
| 5 | `program/generate.cpp:3371` | `prime_hw_queues()` 的调用点 | 同 #4 | 与 #4 一起改，否则函数存在但没人调 |
| 6 | `prefill/prefill.cpp:2871` | CPU share 的**默认值**只对 gfx12 | **不是缺口** | 我们显式设 `STRATA_PREFILL_CPU_SHARE`/`_MAX`，默认值走不到 |
| 7 | `verify.cpp:4` | verify 的 CUDA-only 头 | 无关 | 只是头文件包含条件 |

## 2 三个可以零风险解开的开关（`P480`）

2/3/4/5 的共同点：**都是 opt-in 环境变量的实现，默认行为不依赖它们**。把它们改成
`(defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906))` 后：

- 默认起机**完全不变**（三个开关都要求显式 env，且内部还有「仅 gfx12」的默认判据）；
- 得到三个可直接 A/B 的旋钮：
  - `STRATA_MTP_HIP_PRIO=1` —— 草稿流独占高优先级 HW 队列（我们在用 `--mtp`，这条直接影响 decode）
  - `STRATA_COPY_HIP_PRIO=1` —— 拷贝流高优先级（`--pcie-mode dma` 时防止与窗口图抢队列）
  - `STRATA_HIP_QUEUE_PRIME=nn` —— 起机时按确定顺序开两条 HW 队列（**可能正是「重启后第一个请求偏慢」的机制**）

**判据（每个开关单独一次重启）**：decode 侧 `ms/窗` 或 36 题贪心 + 底噪 0；prefill 侧 2K/8K 的 2×CV；默认臂必须与在产**逐位相同**（编译期不改默认 ⇒ 该是 0 差异）。

## 3 反方向：树里也有**专门为 gfx906** 写的代码

不是「一律砍 gfx906」：

| 位置 | 内容 |
|---|---|
| `core/verify.cpp:2210` | `moe_route_window`：gfx906 的 256 专家 router 整窗一次 BF16 投影 + 一次 top-k，与逐 token **bitwise** 相同（2×MI50 上 ~55 ms 窗口里省 3 ms） |
| `core/expert_source.cpp:934` | gfx906 专用的专家来源分支 |
| `kernels/cuda/*` | 我们已在 port-all 上落的 DPP / LDS pad / gather8 等（`P425`–`P452`） |

⇒ 结论：这部分是**维护过的**，所以「gfx906 缺能力」的默认假设不成立，必须逐条看条件。

## 4 下一步（顺序固定）

1. 先测 `kvg`（`--kv-grow`，候选已建、窗口 2 次重启）——它收益最大（+767 槽 @16K）。
2. 若 `kvg` 通过，再单测 `STRATA_HIP_QUEUE_PRIME=nn`（它可能顺手解释「重启后首请求慢」）。
3. 逐个测 `STRATA_MTP_HIP_PRIO` / `STRATA_COPY_HIP_PRIO`（decode 侧判据）。
4. 任何一条都遵守「改条件 → 二进制变了才算改到」（`P473`），并用 `nm -D` / `strings` 做静态复核。

## 5 九十三处总账（`R105` 收口，W1052 实测枚举）

> `$ grep -rn STRATA_HIP_GFX906 src include third_party | wc -l` = **93**（原始出现行数）。
> 分类判据沿用 §1 的三问：① 排除的是硬件能力还是 API/工具链不存在？② 有无运行时判据可替代？
> ③ 缺的功能对生产参数面是否可达？**结论先行：93 处里真正的「硬件能力缺口」只有 3 处，
> 且 3 处都不损失生产功能**；可翻案的假设 8 处（其中 5 处已点名处理）；其余是 API/平台分工/构建开关/无关。

| 类 | 处数 | 判定 | 代表位置 |
|---|---|---|---|
| **A. 正向门（为 gfx906 写的优化）** | 60 | 维护过，不是缺口 | `qsa_decode_attn.cu`（DPP/swizzle/OPT 位）、`iq_kernels.cu`、`fused_gr.cu`、`router_top10.cu`、`generate.cpp`（`USE_HIP \|\| GFX906` 合流）等 |
| **B. 硬件事实（真排除）** | 3 | ①硬件：gfx906 无 `permlanex16`/DPP row_xmask（gfx10+）；wave64≠wave32 | `s26_tsum.cuh:14`（permlanex16）、`verify_kernels.cu:832`（wave32 族）、`qsa_decode_attn.cu:466`（pre75/DPP 变体不建） |
| **C. 撰写时假设 / 可选开关被编译掉** | 8 | ②可翻案（运行时判据或 env 已存在）；③默认不损失 | 已点名 5：`mtp.cpp:486`（MTP 高优先队列）、`verify.cpp:1213`（copy 高优先队列）、`generate.cpp:3078/3371`（prime_hw_queues）、`expert_cache.cpp:101`（cudaDevAttrIntegrated，注释自证"该卡恒 discrete"）；另 3：`prefill.cpp:2863/2871`（CPU share 默认值，**不是缺口**——我们显式设 env）、`qsa_prompt_attn.cu:2458`（prompt 侧 gated 变体；B2/P435 已证 gfx906 预填走 `qsa_decode_attn_batch`，此路径不可达） |
| **D. API/工具链不存在（非硬件）** | 16 | ①是 CUDA/HIP API 面差异或版本绑定，不是 MI50 少能力 | `vmm.cpp:3`（CUDA 头选择）、`mtp.cpp:479`、`verify.cpp:4/239/1178/1190/2763/2878/4409/4425/4444`（CUDA graph 优先级族）、`generate.cpp:2060`（PCI 总线/进程查询）、`generate.cpp:7421`（CUDART 版本检查）、`dma_batch.hpp:68`（CUDA13 批量拷贝 API）、`mmvq_il_parity.cpp:88/493`（L2 accessPolicyWindow，parity 工具） |
| **E. 构建开关 / 其它无关** | 6 | 实验特性或专用卡路径 | `iq_kernels.cu:4326`（SM60 实验 down-WS）、`expert_nibble.hpp:33`（SM60 实验）、`iq_kernels.cu:6151/6313`（gfx1151/V2K 检测）、`gr_parity.cpp:461`（wave32 测试覆盖）、`verify.hpp:511`（graph prio 成员） |

**处置**（§2 的三个 opt-in 开关仍按原计划，收益面不变）：
1. C 类中 `mtp.cpp:486` / `verify.cpp:1213` / `generate.cpp:3078+3371` 三组可零风险解开（默认行为不变，见 §2）；
2. C 类的 `expert_cache.cpp:101`：注释已自证（gfx906 恒 discrete），解开只影响混插 APU 场景——**不动**；
3. `prefill.cpp:2863/2871` 与 `qsa_prompt_attn.cu:2458` 生产不可达，**不动**；
4. B 类 3 处是真硬件事实，**不动**；
5. D/E 类与生产参数面无关，**不动**。

⇒ **R105 收口：「gfx906 少掉的能力」清单 = B 类 3 处（均无生产损失）+ C 类 5 处（可翻案、已点名、默认关）。**
