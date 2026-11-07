# W775delta W20 ---- EXT 清单逐项复核（触发条件 2026-10-11 17:37 已兑现）

> 机主令（2026-10-11 19:5x）：「回溯有没有该固化的没固化、该落生产的没落……其他你继续推动」=> 本轮推进 `W20`。
> 触发条件（`W775delta_EXT_VALUE_REGISTER.md` §0 立）：**改驻留模式 `--resident-*`** ---- **已于 2026-10-11 17:37 兑现**
> （`--resident-budget-gib 76` -> `--resident-experts` + `STRATA_RESIDENT_HEADROOM_GIB=0.5`；`P09` 废 / `P66`+`P65` 采纳）。
> 做法：0 发车、只读源码与账本；逐行判「该行的『本机为何不用』是否挂在驻留模式上」。

## 0 结论（先行）

1. **13 行里只有 1 行需要重述**：**`P54`**（`STRATA_IO_PREFETCH`）---- 它的理由**逐字引用了已废的 `76 GiB` 预算**。
2. **其余 12 行不受本次触发影响**：它们的"本机为何不用"分别挂在 `--kv`（`P55`/`P56`）· native pack（`P52`）· PLE 表已加载、被自动切 mmap（`P58`；2026-10-14 更正）· 单卡（`P53`）· 硬件面（`P57`）· 贪心解码（`P29`）· 我方实测数据（`P36`/`P37`/`P40`/`P45` + §2 的 `Q8_PACKED`/`Q6_PACKED`）---- **与 `--resident-*` 无关**。
3. **新增 1 项 EXT**：**`P09 --resident-budget-gib`** ---- 我们已废（因为它设计性关闭借区），但它对**小 RAM 预算的用户**仍是有效的内存上限旋钮 => 按新规则第 4 问应带 `[EXT: 小 RAM 预算]`。
4. **上游**：`#1926` **open / 0 评论**（无回音）；`#1923` **open / 2 评论**（均为我方，无上游回复）=> 无新动作。

## 1 逐行复核表

| ID | 标的 | 原「本机为何不用」挂在 | 本波（`--resident-*` 变更）影响 | 处置 |
|---|---|---|---|---|
| `P55` | `STRATA_GFX906_ATTN_QUERY_SWIZZLE` | `--kv k8v4` => `kv_mode=3`，路径恒假 | **无** | 理由不变 |
| `P56` | `STRATA_GFX906_ATTN_REDUCE12` | 依赖 `P55` | **无** | 理由不变 |
| `P52` | `--dump-logits` / `--logits-stride` | 我们走 **native pack** | **无** | 理由不变 |
| `P58` | `STRATA_PLE_PROBE` / `--ple-io` | args 无 `--ple-io`/`--ple-gguf` | **无** | 理由不变 |
| **`P54`** | **`STRATA_IO_PREFETCH`** | **"本机 128 GiB RAM + **`--resident-budget-gib 76`** => page cache 已存 ~78 GB 专家 => 预取对象≈0（实测 0 次）"** | **有**：该 flag **已废**（`P09` -> REJECTED），现行是 `--resident-experts`（无预算）+ 补集 **36.93 GiB**（含借区） | **重述（见 §2）** |
| `P53` | `--layer-split` / `STRATA_USE_HIP` 宏面 | 本机单卡 | **无** | 理由不变 |
| `P57` | v0.1.42 非 gfx906 新开关族 | 多卡/Intel/gfx12/Windows 硬件面 | **无** | 理由不变 |
| `P29` | `STRATA_SPEC_GUMBEL` | 我们默认贪心解码 | **无** | 理由不变 |
| `P36` | `STRATA_EXPERT_V2` | gfx906 实测 **-5.60%** | **无** | 理由不变 |
| `P37` | `STRATA_TSUM` | gfx906 不可复现 | **无** | 理由不变 |
| `P40` | `STRATA_SH_STREAM` | 本 pack **-0.13%** | **无** | 理由不变 |
| `P45` | 非专家张量精度路线 | 实读已是 Q8_0 | **无** | 理由不变 |
| `Q8_PACKED` / `Q6_PACKED`（§2） | 同族 decode 布局 | 本机实测无增益 + 1.87 GiB | **无** | 理由不变 |

## 2 `P54` 的重述（唯一实质改动）

**旧**（挂在已废 flag 上）："本机 128 GiB RAM + **`--resident-budget-gib 76`** => page cache 已存 ~78 GB 专家 => 预取对象≈0（实测 0 次）"

**新**（挂在现行配置上，并**据实加强**）：
> 本机 128 GiB RAM；现行驻留模式 = **`--resident-experts`（无 RAM 预算）+ `STRATA_RESIDENT_HEADROOM_GIB=0.5`** => 补集 **36.93 GiB**（含 prompt 路借区 1,554 槽 / 3.49 GiB），
> 且 **B7 固化后稳态 = `0 blob reads from the file`、`file tier ... for 0.0 MB of expert reads`**（`W775delta_W4X_RES_RESULT.md` §8/§11）。
> => 预取对象**比 `W773` 实测时（≈0）更少**：`[EXT: 小 RAM 预算]` 的适用面不变，且**本机现在更确定地不受益**。
> 复现：`GET /metrics`（`engine.spec`/`mtp_max`/`lookup` 等）与产线日志的 `resident RAM` / `file tier I/O this request` 行。

## 3 新增 EXT 项：`P09 --resident-budget-gib`

| ID | 标的 | 本机为何不用 | 对外适用面 | 标签 |
|---|---|---|---|---|
| **`P09`** | `--resident-budget-gib` | **设计性关闭借区**（`expert_source.hpp:550-552` 逐字 *"No lend region then"*）：`budget_bytes > 0` => `lend=false` => prompt 借走的槽每 chunk 从模型文件补回。B7 实测换掉它后冷 read_ms **-2.50%**（区间不重叠） => **本机废止** | **RAM 预算紧张、必须给引擎设内存上限的机器**：这条是**唯一**能在启动期把页锁定补集压下来的旋钮（`expert_source.cpp:2649-2650` `budget = available - headroom`）---- 我们的场景是 RAM 宽裕（128 GiB）才敢不用它 | `[EXT: 小 RAM 预算]` |

## 4 上游状态（现查）

| 号 | 状态 | 评论 | 说明 |
|---|---|---|---|
| `#1926` | **open** | **0** | 我们发的四条 doc-level notes，**无回音** |
| `#1923` | **open** | 2（均我方 `6106275361` / `6106666399`） | 无上游回复；我方第二条是主动 qualification（撤回生产增益主张） |

## 5 落账

- 本件为新产出；`W775delta_EXT_VALUE_REGISTER.md`：`P54` 行重述 + 新增 `P09` 行 + 顶部加「W20 复核（2026-10-11 19:5x）」记录。
- `PARAM_REGISTER.tsv`：`P54` verdict 追加（**status 不动**，仍 CANDIDATE）、`P09` verdict 追加 `[EXT: 小 RAM 预算]`。
- `W750` 的 `W20` 行标「逐项复核已完成」。

## 6 局限

- 复核判据是「该行理由是否引用 `--resident-*`」，属**文本级**判断；未在别的配置上实测（那本就不是本文的目标）。
- `P09` 的 `[EXT: 小 RAM 预算]` 是**机制级**推断（该 flag 的语义就是设 RAM 上限），未在真小 RAM 机器上验。
