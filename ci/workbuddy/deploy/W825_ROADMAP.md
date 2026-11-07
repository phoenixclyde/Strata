# W825 · 三轮复盘与下一步计划

> **【角色声明 · R44/AUDIT23，2026-11-02 02:1x】本文是历史复盘，**§4「下一步计划」不是队列**。**
> 本项目唯一方案权威是 `W832_OPT_PLAN_V2.md`，唯一排序处是其 **§6.5**。
> **§4 的 P0（跑上游 `tools/calibrate.py` 做官方标定）已经执行完毕**：`P160` → `P184`（2026-10-31，55 min，
> 每次重启 255 s），**五项全部结清、无参数变更**（`pcie-frac 0.20` 是扫描最优，但重复性只在单实例内成立；
> 后续 `P210` 同实例重判为 **UNRESOLVED**，保留现值而非「最优」）。
> 所以本文的 P0 不是 "待办"，是 "已办、结论为无变更" —— 引它时别当成还没做的事。

> 时间：2026-10-30 02:05
> 对象：gfx906（MI50 32 GB）× Xeon E5-2696 v4（22C/44T，DDR4-2133）× PCIe 3.0 x16
> 生产：engine **0.1.53** · `--pack ud-q4_k_xl` · env 14 / args 33 · HEALTHY

---

## 0 一句话

过去三轮把「换权重 → 升级 → 调优 → 质量门 → 清盘」这条链走完，**只有一处拿到了真收益：`ATTN_REDUCE12` 的 prefill −3.8%（且已证明逐位等价）**。
升级本身 **0**（x86 产物的实质变更 ≈ 版本号），换权重的提示侧代价**不成立**（见 AUDIT11）；
但在复盘时发现一件比继续调参更重要的事：**我们至少有 3 个核心参数是从未标定过的手选值，而上游提供了官方标定工具，
我们一次都没跑过**。下一步的第一优先级不是再试一个 env，而是**用 `tools/calibrate.py` 把硬件相关参数一次性标定**。

---

## 1 三轮做了什么

| 轮 | 主题 | 结果 |
|---|---|---|
| **W822** | 换权重 `UD-Q4_K_XL` | 工程上完成；不开 `MMQ_KQ` 时 prefill 掉 47%（267 tok/s），开了回到 **稳态 525**（原记 427 是冷启动首请求，AUDIT11 更正） |
| **W823** | 上游复核 + 模型名 | 判定**不升级**（K-quant 路径两版几乎逐字节相同）；`/v1/models` 报旧名，根因是配置里显式 `model_name` |
| **W824-a** | 升 0.1.53 | 文件级移植（codeload 限速）；543/548 文件与上游一致，只有 2 个是有意改的；`dsv41` 字符串 0 ⇒ 差异不进产物 |
| **W824-b** | 调优三臂 | `V2K` 三次无差异（假信号）、`--spec-min-p 0.50` **−14.5%**（否）、`ATTN_REDUCE12` **prefill −3.8%**（采纳） |
| **W824-c** | 质量门 | 底噪来源查明（`share=auto`）；`share=0` 下三份 LOGPOS **同哈希** ⇒ reduce12 **逐位等价** |
| **W824-d** | 清盘 + compat 裁定 | 删 IQ4 两份独立副本 **174.5 GiB**；`--compat-bf16` 的舍入**在我们这种 `--native`+`HC_Q8=1` 下不生效**（读原始 Q8_0） |

### 本轮新增的四条（刚刚查证，此前未记录）

| # | 事实 | 出处 |
|---|---|---|
| 1 | **上游有官方标定工具 `tools/calibrate.py`**，`python3 calibrate.py <cfg.json>` 直接跑；标定 `--pcie-frac` / `--spec-min-p` / `--pool-workers` / `--adapt-*` / `--prefill-pipe` / **`STRATA_SH_STREAM`（AMD 专属）**；判据 `MIN_GAIN=3%` + 交错重测 | `tools/calibrate.py:1-33, 49, 525` |
| 2 | **`STRATA_SH_STREAM`**：`Off by default on HIP`；上游实测同一卡族在另一台机上 **6-11% 更快**、另一台 **12-45% 更慢** ⇒ **必须逐机测**；且**输出相同（same token ids）** | `calibrate.py:24-28` |
| 3 | **`--adapt-*` 在"老 Xeon + 慢内存"上实测 +7.9%**（Xeon E5-2673 v3 + DDR3 + RTX 4060 Ti PCIe 3.0 x8，`--adapt-swaps 160`）——**我们的硬件画像与它高度接近**，而这三个参数我们从未设过 | `calibrate.py:18-22` |
| 4 | `STRATA_TSUM` 在 gfx906 **可用**（fallback `__shfl_xor_sync`），但上游自家 harness 说 **gate/up 用它是 0.6-0.8x（更慢）**，只有 down rows 是 1.09-1.12x ⇒ 不采纳 | `s26_tsum.cuh:12-27`、`iq_kernels.cu:6269-6272` |

---

## 2 当前实况

```
exe   /data/bin/strata-0.1.53          pack  /data/packs/ud-q4_k_xl
env14 HSA_OVERRIDE 9.0.6 · GDN_HEAD 1 · GDN_PP 2 · ATTN_QUERY_SWIZZLE 1 · ATTN_REDUCE12 1
      HC_Q8 1 · HIP_PROMPT_F16 1 · MMQ_KQ 1 · PREFILL_CPU_SHARE auto · _MAX 3072
      RESIDENT_HEADROOM_GIB 0.5 · ROCBLAS_TUNING /data/gfx906-rocblas-5.5.0.txt
      ROUTE_TAIL_SKIP 7 · SELECT_SIMT 1
args  --spec 4 · --spec-min-p 0.70 · --pcie-frac 0.20 · --expert-cache auto · --kv k8v4
      --prefill auto · --mtp /data/mtp/rt · 无 --pool-workers / --adapt-* / --suffix-draft（默认 3）
槽位  7551 / 22.04 GiB（覆盖率 30.7%=7551/24576）· 磁盘 238 GB 可用 · MemAvailable 46.6 GB
```

**prefill 时间构成**（4563 token，reduce12 生效后，GPU timeline 6765 ms）：
`gate/up 22.7%` · `down 14.7%` · `attn 12.0%` · `gdn 11.8%` · `dequant 9.1%` · `hc read 8.7%` · `qsa proj 5.3%` · `ple 0.5%`
而 **decode 占一轮 64-83%**（W798）。

---

## 3 复盘发现的四个结构性问题

### 3.1 【最重要】核心参数是手选的，从未标定

| 参数 | 我们的值 | 上游依据 | 问题 |
|---|---|---|---|
| `--pcie-frac` | **0.20** | calibrate 说"默认值是按 Ryzen 5 7600 + RTX 5070 + **PCIe 5** 测的" | 我们是 **PCIe 3.0 x16 + DDR4-2133 + 老 Xeon**，与前提差两代 |
| `--spec-min-p` | **0.70** | setup 写 0.5；calibrate 能测 | 0.70 是手选的；测过 0.50 亏 14.5%，但**没有测过 0.5-0.7 之间的最优点** |
| `--pool-workers` | **未设**（默认） | calibrate 专测（"所有物理核不总是最好"） | 44 线程的机器上，默认值未必对 |
| `--adapt-every/swaps/decay` | **未设** | calibrate 专测；**老 Xeon + 慢内存上 +7.9%** | 我们的内存 DDR4-2133，比那台 DDR3 快但远慢于 DDR5 |
| `STRATA_SH_STREAM` | **未设**（HIP 默认 off） | calibrate 专测；**12-45% 幅度、输出相同** | 从没测过 |

⇒ 这五项**全部**是"上游用另一台机器测出的默认值，而我们直接沿用了"。`calibrate.py` 一次能覆盖前四类中的三类多。

### 3.2 数值债账本：8 个"会改 bits / 未在本机验"的开关，一个都没量过 KL

| 开关 | 当前 | 源码措辞（逐字） | 位置 |
|---|---|---|---|
| `STRATA_ROUTE_TAIL_SKIP` | **7** | `(default 7 on CUDA serve, =0 off; **changes the output**): … its contribution is zero, without renormalisation` | `expert_source.cpp:4887` |
| `STRATA_HIP_PROMPT_F16` | **1** | `It **changes the prompt path's numbers** (an FP16 rounding of …)` | `gemm.cu:588` |
| `STRATA_MMQ_KQ` | **1** | `opt-in: **other rounding** than the FP16 path` | `mmq_kq_abi.hpp:22` |
| `STRATA_SELECT_SIMT` | **1** | `**its sum order differs** from the warp kernel's` | `qsa_select.cu:2256` |
| `--kv k8v4` | **k8v4** | `INT8 K (exact attention scores) + **rotated Q4_0 V**, 816 B/cell` | `generate.cpp:908` |
| `STRATA_HC_Q8` | **1** | 上游分类：`rounding-level, **KL-gated**` | `arch_defaults.hpp:8` |
| `STRATA_GDN_HEAD` | **1** | **来自 gfx1151 的 exact 表**（`arch_defaults.cpp:61`，Aurora/S23 上 byte-identical 验证）—— **但不是在 gfx906 上验的** | `arch_defaults.cpp:61`、`prefill/kernels.cu:1266` |
| `STRATA_GDN_PP` | **2** | 同上（`arch_defaults.cpp:62`，"the same arithmetic in the same order"） | `prefill/kernels.cu:1375` |

> **AUDIT11 补**：这两个是"从别的架构抄来、理论上 exact、本机从未验过"的一类，与 RT_SKIP/kv 那种"上游明说会改位"不同，
> 风险低——但账上不能留空。所以数值债是 **8 项**，不是 6 项。

**账上从来没有一个数回答"这些叠在一起值多少 KL"。** 这比任何单项更重要——因为它决定：
- 我们对外承诺的"质量"到底是什么档；
- 换更大/更小 pack 时的收益基线；
- 上游给的 0.003-0.006（单 RT_SKIP）在我们这套上是否成立。

### 3.3 测量方法学（四次踩坑换来的）

1. **跨容器比 decode 无效**：同配置 N0 41.8 → N0b 46.9（+12%）、A 39.4 vs A2 45.8（+16%）⇒ 必须 **ABBA 交错 + 同阶段样本**。
2. **teacher-forced 质量门必须先固定 `share=0`**：否则底噪（0.025）与效应（0.026-0.046）同量级，只能得"判不了"。
3. **驱动脚本必须互斥**：两个驱动抢同一容器名，后起的 `rm -f` 会删掉前一个的容器（V1 因此丢数据）；互斥用 **flock**，`pgrep -f` 会匹配到自己。

4. **【AUDIT11 新增，最重要】必须先预热 2 轮**。首请求带约 **1.0 s** 冷启动
   （原始件 `w816_det` 的 `TR` 行：`1018.3 ms` → `167.7 ms` → 稳态 `57-65 ms`）。
   我们的 `mt_read.py` **一直没有预热**，于是三件事同源：
   ①W822 的"生产 427"是首请求值，稳态 **525**；
   ②**短档方差 4.6%（1453）与长档方差 0.1%（4568）是同一件事** —— 短档是冷启动档，长档是第三档（已热）；
   ③W810 的前两档各多 265 / 398 ms（用 `t = a + b·n` 拟合得 `a=220 ms, b=1.732 ms/tok` 后反推）。

   **上游工具早就这么做了，我们没照做** —— `tools/calibrate.py`：

   ```python
   def warm_up(self, rounds: int = 2)          # 默认预热 2 轮
   SWEEP_ROUNDS = 3                            # 每个值扫 3 轮，顺序交替（ABBA）
   if len(gains) == SWEEP_ROUNDS and min(gains) > 0.0 and median(gains) > MIN_GAIN   # 每轮都赢 + 中位超 3%
   ```

   ⇒ **协议定稿**：每个新容器先 `warm_up=2`（`mt_read.py` 已加第 8 个参数、默认 2，并写进输出 JSON 的 `warm_wall`）；
   判据从"单次 ≥5%"改为「**每轮都赢 + 中位超阈值**」，轮数 3、顺序交替。
   W824 的 A/A2 在 1453 差 4.6%、在 4568 只差 0.1%，**不是二进制的差异，是冷热档的差异**。

### 3.4 登记表治理：同一开关多 ID、状态不同步

156 行里有 10 条 CANDIDATE，但其中至少 4 条**实际已在生产运行**：

| ID | 开关 | 登记状态 | 实际 |
|---|---|---|---|
| P55 | `ATTN_QUERY_SWIZZLE` | CANDIDATE | **生产开着** |
| P56 | `ATTN_REDUCE12` | CANDIDATE | **生产开着**（且 P156 已 ADOPTED —— 重复登记） |
| P105 | `ROCBLAS_TUNING` | CANDIDATE | **生产在用**（env 指向 gfx906 表） |
| P106 | `SELECT_SIMT=2` | CANDIDATE | 生产是 `=1`（P106 说的是 =2，未测） |

⇒ 账本失真：一眼看"10 条待办"，实际只有 6 条是真空缺。**治理不清，后面的优先级排序都建在错账上。**

---

## 4 下一步计划

### P0 · 官方标定（推荐第一件事）

**做什么**：`python3 tools/calibrate.py <副本配置.json>`，产出它自己选的 `--pcie-frac` / `--spec-min-p` / `--pool-workers` / `--adapt-*` / `STRATA_SH_STREAM`。

**为什么先做它**：
- 一次调用覆盖 **5 类参数**，其中 3 类（`--pcie-frac`、`--spec-min-p`、`--prefill-pipe`）**在单实例内用 `strata_tune` 测多组，不用反复重启**；
- 判据是上游自己的：**每轮都赢 + 中位超 3%** 才保留（比我们的"≥5%"更细，但要求更严）；
- **它自带 `warm_up(2)` + `SWEEP_ROUNDS=3` + 顺序交替** —— 这三件事我们的自制脚本一件都没做（见 §3.3 第 4 条），
  所以跑它同时也把我们的测量协议校准到上游标准；
- 它测的正是"我们与上游默认值前提不同"的那几项。

**前置**：必须独占 GPU ⇒ 停生产。副本配置（不碰生产）；`STRATA_PREFILL_CPU_SHARE=0`（避免它自己的测量被 auto 噪声污染 —— 这点要确认它内部是否已处理）。

**成本**：一次窗口，预计 30-45 min（含 3-4 次重启，因为它说 worker count / adapt / SH_STREAM "need a restart per value"）。

**判据**：它返回的 JSON 里每个胜出项的增益 ≥3%；我们再用 ABBA 在生产上复核一次（≥5% 才采纳，沿用本机规矩）。

**风险**：它**会写回配置**（`apply_args` / `apply_env`）⇒ 只用副本，产出候选值后人工审。

---

### P1 · 数值债总量二分（一次窗口，2 臂）

**做什么**：在 `share=0` + LOGPOS 下，量 **当前全量 vs "最小近似"**：

| 臂 | 配置 |
|---|---|
| E0 | 生产全量（RT_SKIP=7、k8v4、PROMPT_F16=1、SELECT_SIMT=1、MMQ_KQ=1、HC_Q8=1） |
| Eall | RT_SKIP=0、`--kv fp16`、PROMPT_F16=0、SELECT_SIMT=0、HC_Q8=0（MMQ_KQ 保留，否则 prefill 慢 71% 且它只是"另一种舍入"） |

**为什么这样设计**：不去逐个关（6 项 × 2 = 12 次启动），而是**先量总量**——
- 若总量 KL < 0.02 ⇒ 所有单项都不值得再查，账本直接结清；
- 若总量 KL > 0.05 ⇒ 再做二分（先分"专家路径 RT_SKIP" vs "数值路径"两组）。

**判据**：底噪必须是 0（三份文件同哈希，P158 已验证该方法可行）；总量给出后按 0.02 / 0.05 分档结论。

**成本**：2 臂 × (启动 ~3.5 min + 测量 ~2 min) ≈ 12-15 min。

**产出**：账本上第一次有"我们的近似总共值多少 KL"这个数。

---

### P2 · 有可信标尺的速度项（按性价比，逐条独立）

| # | 项 | 作用面 | 判据 | 预期 |
|---|---|---|---|---|
| 2.1 | `STRATA_SH_STREAM=1` | decode（AMD 专属，输出相同） | `ms/window`（decode timing）+ ABBA | **12-45% 幅度**，方向未知，必须实测 |
| 2.2 | `--adapt-swaps 160` 等 | decode（VRAM 层跟随对话） | 同上 | 老 Xeon 上上游测到 **+7.9%** |
| 2.3 | `--spec 5/6` | decode（verify 窗口更大） | `tokens/window ÷ ms/window` | 槽位覆盖 30.7%，窗口越大 miss 越多，可能负 |
| 2.4 | `--prefill` chunk（4096/2048） | prefill 的 gate/up + dequant | 相位表（重复性 0.1%） | PLE 已 0.5%，旧结论（+5~9%）要重测；chunk 边界影响专家 gather 复用 |
| 2.5 | `dequant 9.1%` 相位归因 | prefill | 相位表 | 先搞清它随什么变，再决定动不动 |

其中 **2.1 / 2.2 已被 P0 覆盖**（calibrate 会测），所以 P2 真正独立的是 2.3 / 2.4。

---

### P3 · 需要写代码的（有明确上游依据，收益可估）

| # | 项 | 依据 | 收益估 | 风险 |
|---|---|---|---|---|
| 3.1 | 移植 **#3220** 的 HC_Q8 prefill 反量化向量化（8 个 int8/线程 + `uint4` 16 B 写 + pair-fused） | 上游在 gfx1201 上 `3.204 ms → 1.646 ms`（**1.95x**）、T=2048 省 14.0 ms、T=4096 省 21.8 ms，**bitwise identical** | 我们 `hc read` 占 8.7%（586 ms/4563 tok）；若其中 dequant 占比与上游类似，可省 **1-2% prefill** | 低（bitwise），但要重写 HIP 分支并自验 |
| 3.2 | 移植 **#4105** 的 PLE 表 O_DIRECT 读入锁定内存 | 冷启 310 s → **23.7 s**（1215 MB/s），mlock 5.8 s | **0**（`ple` 已 0.5%） | —— |

⇒ **3.2 明确不做**（见 §5）。3.1 值得排到最后，因为它要动内核代码。

---

### P4 · 治理（零停机，随时可做）

1. 合并登记表重复项：`P55/P56` → 并入 `P156`（状态 ADOPTED）；`P105` 改 ADOPTED；`P106` 保留 CANDIDATE 但写清"生产是 `=1`，`=2` 未测"。
2. 把 §3.2 的六项数值债登记成一张**独立清单**（不是散在各 ID 里），标注"未量 KL"。
3. 把 §3.3 三条方法学写进 `PARAM_REGISTER` 的判据说明（或单独 `MEASURE_RULES.md`）。

---

## 5 明确不做（附理由，避免重复讨论）

| 项 | 理由 |
|---|---|
| **#4105 / `--ple-io ram`（P141）** | `ple` 在 Q4_K_XL 上只占 **0.5%**（W810 时在 IQ4_XS 上是 12.9-16.7%）；同一改动的价值掉了 25 倍。且要做需 **26.8 GiB 常驻**（MemAvailable 46.6 GB），换来 0.5% 的稳定性——不划算 |
| **`--ulimit memlock=-1`（P147）** | 它只服务于 P141；P141 已不值得做 ⇒ 顺延 |
| **`STRATA_TSUM=1`** | gfx906 fallback 可用，但上游 harness 明确 **gate/up 是 0.6-0.8x（更慢）**，只有 down 1.09-1.12x；而 gate/up 是我们最大相位 ⇒ 组合下来必然亏 |
| **`STRATA_EXPERT_NIBBLE`** | `#if STRATA_EXPERT_NIBBLE_BUILT`，只在 `STRATA_EXPERIMENTAL_SM60`（CUDA）构建；HIP 上 `gu_nib` 直接 `exit(1)` ⇒ **结构性不可用**（同 `DENSE_MMQ` 一类） |
| **`STRATA_DENSE_MMQ`（P157）** | 同前，`STRATA_PREFILL_MMQ` 与 `STRATA_HIP_GFX906` 互斥 |
| **`STRATA_FILE_CACHE_OLD_RULE=0`（P151）** | gfx906 故意留旧规则（#1752：文件层停止冲刷页缓存后 prompt 46→360 tok/s） |
| **换 Q5_K/Q6_K pack** | `STRATA_Q6K_EXPERTS=OFF`（本构建）；且 arena 91.6/101.7 GiB 放不下 |
| **升级到 0.2.8** | 上游最新仍是 v0.2.7/引擎 0.1.53，main 停在 10-28，41 小时无 x86 Qwen 提交 ⇒ **我们已在上游最新** |
| **`STRATA_EXPERT_V2K`（P153）** | 三次测（含配对）均 0.0% |

---

## 6 顺序与成本总表

**所有窗口统一按 §3.3 协议执行**：每个新容器先 `warm_up=2`（`mt_read.py` 默认已改）；判据取 **3 轮交替（ABBA）的中位**，
并要求**每轮都赢**才采纳 —— 这是上游 `calibrate.py` 的判法，比我们原来的"单次 ≥5%"严格。
预热的代价是约 10 s/臂（2 个短请求），可忽略。

| 优先级 | 项 | 需停生产？ | 时长 | 判据 | 预期 |
|---|---|---|---|---|---|
| **P0** | `calibrate.py` 标定 5 类参数 | 是 | 30-45 min | 它自报 ≥3% + 我们 ABBA ≥5% | `SH_STREAM` / `adapt-*` 可能有两位数 |
| **P1** | 数值债总量 KL（2 臂） | 是 | 12-15 min | 底噪=0；总量 0.02 / 0.05 分档 | 结清最大一笔账 |
| **P2** | `--spec 5/6`、`--prefill` chunk | 是 | 各 12-15 min | `ms/window` / 相位表 | 未知，机制上偏负 |
| **P3** | 移植 #3220（HC_Q8 向量化） | 否（编译）/ 是（验证） | 半天 | 相位表 `hc read` ≥5% | 1-2% prefill |
| **P4** | 登记表治理 | **否** | 20 min | —— | 账本准确 |

**建议今晚就做 P4（零停机）+ 把 P0 排进下一个窗口**；P0 与 P1 可以合并进同一个窗口（都只需停一次），总时长 45-60 min。

---

## 7 一句话记住

> 三轮下来，我们从"盲试开关"走到了"有零底噪标尺"。
> 下一步该做的不是再试一个 env，而是**先把自己跟上游默认值的前提差异标定掉**（calibrate），
> **再把已经开着的近似一次性量清**（数值债总量）。
> 这两件事都不新增任何功能，但它们决定后面每一个判断是否站在真实基线上。
