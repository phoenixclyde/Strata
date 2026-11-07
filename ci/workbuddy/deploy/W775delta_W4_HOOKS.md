# W775delta W4 ---- 逐桶账钩子勘察（`W749-B3` 的前置「摸钩子」，0 发车）

> 触发：`W750 §4` 的 **W4 = 逐桶账定位长上下文**（`W749-B3`）—— 该行原写「**需先摸钩子；可能 0**」。
> **[2026-10-11 20:06 已实测]** 本件的方案**已执行**（真发车、停机 6 min、已恢复）=> **结果见 `deploy/W775delta_W4_BUCKET_LEDGER.md`**；
> 执行中发现本件 §1 的一条须更正：**`--gpu-stages` 对 native（IQ）pack 会直接报错退出**（`generate.cpp:5727` 的 #610 分支），
> 因此实际用的是 **`STRATA_DECODE_TIMING=1` + `STRATA_VERIFY_PROFILE=1`**（`--serve` 模式，`DETAILS.md:298`）---- 那两个才是对所有 pack 通用的钩子。

> 做法：只读 0.1.42 引擎自带 **help**（`deploy/tmp/_w773_help_full.txt`，39,074 B / 451 行，W773 实抓）+ 源码树。**0 发车、生产未动。**

## 0 结论（先行）

1. **钩子现成，不必插桩**：引擎自带 **`--gpu-stages`** ---- help 逐字 *"R0.9: **capture the layer as three graphs (mixer / ffn+router / post) and time them from OUTSIDE the capture**. The per-stage table … **a real graph that `--stage-timing` cannot give. Prints and exits.**"*
   => 这正是 routeK 那条「CUDA-event 包住代表性模块」的**引擎原生版**（**三桶 + 外部计时**）。
2. **配套**：**`--gpu-only-full`** = *"replay pre+post for all 48 layers plus the LM head, no pool. **THE TRUE PER-TOKEN GPU FLOOR**. Quote this one, not `--graph-only`."* => 给出「每 token 的 GPU 地板」，作为桶账的**分母**。
3. **`--stage-timing` 单独用不了**：help 逐字 *"per-stage **KERNEL-COUNT** shares. **NOT a time profile**: an uncaptured event interval includes host gaps, so run with `--gpu-only-full` first"* => 它是**计数面**（与 `W749-B3` 的原始判断一致）。
4. **成本 = 一次"停机窗口"，不是一次改代码**：`--gpu-stages` / `--gpu-only-full` 属 MEASURE 类（*"Prints and exits"*），但**要加载模型**（约 22 GiB VRAM）=> 与现役生产（`vram_free_mib=574`）**不能共存** => 需停生产或另起实例。
   => **最优路径：搭下一次车（本就要停/重启生产）的窗口顺带跑，零额外停机。**

## 1 钩子清单（0.1.42 help 逐字，`_w773_help_full.txt`）

| 钩子 | help 逐字要点 | 面 | 对 W4 的用处 |
|---|---|---|---|
| **`--gpu-stages`** | *"capture the layer as **three graphs (mixer / ffn+router / post)** and time them from **OUTSIDE** the capture … Prints and exits"* | **时间** | **主钩子**：直接给三桶耗时 |
| **`--gpu-only-full`** | *"replay pre+post for all 48 layers plus the LM head, no pool. **THE TRUE PER-TOKEN GPU FLOOR**"* | **时间** | 桶账分母 / 地板 |
| `--stage-timing` | *"per-stage **KERNEL-COUNT** shares. **NOT a time profile**"* | 计数 | 辅助（核桶覆盖） |
| `--stats` | *"print the per-stage breakdown"* | 计数 | 辅助 |
| `--dump-layers` | *"write R after EVERY layer, per position: **the C1 bisection ladder**"* | **数值** | 层定位（非时间） |
| `--dump-halves` | *"both halves' block_out and inject per layer: the half bisection"* | 数值 | 半定位 |
| `--dump-routing` | *"the routed expert ids and weights per layer per position"* | 数值 | 专家面（非 attn 面） |
| `--sync-every-layer` | *"debug: synchronise after every layer"* | 调试 | 可测「异步掩盖」，但**会改变性能特征**（不作定量） |
| `--graph-only` | *"replay the 48 `pre` graphs only. OMITS the 48 `post` graphs and the LM head, so it is **NOT the GPU floor**"* | 时间 | **不要用它**（help 明确警告） |

## 2 为什么不需要照搬 routeK 的插桩

- routeK 的 `PROFILE-k4-step-ledger.md` 用**自插 CUDA-event** 把一步拆成 `full_attn / lin_attn(GDN) / mlp / drafter / head`，桶覆盖 ~100%、step-bracket 与端到端差 ~2%（结论：**full_attn 是唯一随上下文增长的桶**，64k->120k 增长里占 87%）。
- 本引擎把同类信息做成了**原生开关**（`--gpu-stages` 三桶 + 外部计时）= 等价物，**无需改一行代码**。
- 粒度差异：routeK 5 桶（含 drafter / 各 head），本引擎 **3 桶（mixer / ffn+router / post）** => **够回答"长上下文慢在哪个桶"**，但**不足以**再细分到 GDN/attention 内部；若要更细，仍回 `--dump-halves`（数值面）+ 源码。

## 3 建议方案（搭下一次车的窗口，零额外停机）

| 臂 | 配置 | 读什么 |
|---|---|---|
| **L** 长档 | 现役 args + `--gpu-stages` + 长 prompt（如 128k） | 三桶耗时 + 总 |
| **S** 短档 | 同 args（**只换 prompt 长度**）+ `--gpu-stages` | 三桶耗时 + 总 |
| **F** 地板 | `--gpu-only-full`（同两档） | TRUE PER-TOKEN GPU FLOOR |

**判读**：比较 **(L - S)** 的**三桶增量** ---- 增量集中在 `mixer` 即"attention 主导"，在 `ffn+router` 即"专家/FFN 主导"，在 `post` 则另查。
**纪律**：`Z0=off`；两档**同形状**（同 gen、同 batch）；比 `ms/step`；每档 **5+ runs**（本项目 decode spread 16-41%）。
**生产安全**：本测量**不能与现役生产共存**（VRAM）=> 必须落在**已有的发车窗口**里；不新增停机。

## 4 局限

- 本件**未发车**：只做「钩子勘察 + 方案」，**未取任何读数**。
- 三桶的**界内构成**未知（`mixer` 里 attention 与 GDN 各占多少）：help 未展开，须回源码 `--gpu-stages` 的 capture 点确认。
- `--gpu-stages` 是 *"Prints and exits"* 的测量模式：其读数**未必**等于 `--serve` 持续服务的稳态（两者路径可能不同）=> 方案里的 L/S/F 三臂**都在测量模式内比**，才自洽。
