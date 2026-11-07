# ENV_PACKAGING_RULE · 开关该不该合成套装
> **ROCm 版本口径（`W917` 2026-11-03 定稿，不再反复）**：内容 = **10.1.0**（TheRock 源码树 `therock-10.1`、`.info/version` 10.1.0、HIP **7.16.26323**、clang 24.0.0git）；**包名** = `amdrocm-core7.14-gfx906 7.14.0-gfx906+20260802001858`（gfx906 社区栈沿用 7.14 打包基线）。说版本时只写前者，后者仅在指 deb 时出现。

**立** 2026-11-02 01:06（机主令：「你记得，别又忘了，一会合一会儿不合的」）
**已落** `MEMORY.md` §2（`打包:exact=>默认,改比特+交互=>套装,机制/观测=>独立,套装项可单设(P245)`）

---

## 1 判据（四条，按顺序问）

| # | 问 | 答「是」⇒ 处理 |
|---|---|---|
| 1 | 它改变数值输出（不逐字节相同）吗？ | **否** ⇒ 可以进 `*_DEFAULTS` 表，默认开，不需要用户设 |
| 2 | 它改变比特，且与套装里已有开关**交互**（KL 不可相加）？ | ⇒ 进 `*_TUNED` 套装，opt-in，整套验证 |
| 3 | 它改变比特但可单独验证、不与套装交互？ | ⇒ **独立 env**，不要塞进已验证的配方 |
| 4 | 它只改机制（搬运/调度/容量）或只打印？ | ⇒ **独立 env**；观测类永不合并、永不设默认 |

**一句话**：只有「改比特 + 互相交互 + 验证单元是整体」才合；其余一律独立。

## 2 源码依据（不是我的偏好）

`src/core/arch_defaults.cpp:188-190` 逐字：

> gfx906's rounding-level recipe: the switches the production MI50 build runs that are NOT byte-identical,
> so they cannot be defaults. Opt-in as a set (STRATA_GFX906_TUNED=1) because they interact: the KL figures
> below are the teacher-forced LOGPOS measurement of each switch against this same engine, **not a claim that they add up**.

`src/core/arch_defaults.cpp:52-57` 逐字：

> gfx906 … the two switches on this branch that are measured BYTE-IDENTICAL here, so they are on by default
> on this card and nowhere else. Everything else this card's recipe uses changes bits and lives in
> gfx906_tuned_env() below … and **the reason this table has two entries instead of fourteen**.

⇒ 上游作者拆两张表（`*_DEFAULTS` 2 项 / `*_TUNED` 7 项）的唯一理由，就是下面这条分界线。
如果我们把 14 项合在一起，等于取消了「哪些改动是无损的」这个信息。

## 3 当前生产的归类（2026-11-02）

| env | 归类 | 依据 |
|---|---|---|
| `STRATA_GFX906_DEFAULTS` 表：`GDN_HEAD`、`GFX906_ATTN_REDUCE12` | **默认开（无损）** | KL 0.0000 / md5 相等的纯重排 |
| `STRATA_GFX906_TUNED` 表：`ATTN_QUERY_SWIZZLE`、`GDN_PP=2`、`HC_Q8`、`SELECT_SIMT`、`ROUTE_TAIL_SKIP=7`、`MMQ_KQ`、`HIP_PROMPT_F16` | **套装（改比特）** | KL 0.0004–0.0171，注释逐条给出 |
| `STRATA_CKPT_MOVE_PARK` | **独立** | 只改搬运方式，不改比特，不与他项交互 |
| `STRATA_DECODE_TIMING` / `SPEC_DEPTH` / `VERIFY_NODES` | **独立（观测）** | 只打印；合并会导致「为了看一个数被迫开三个」 |
| `PREFILL_CPU_SHARE` / `_MAX` | **独立成对** | 容量/调度，不改比特 |
| `RESIDENT_HEADROOM_GIB` / `ROCBLAS_TUNING` / `HSA_OVERRIDE` | **独立** | 资源/路径/环境 |

## 4 反例：P245 那次「合错了」

`STRATA_PARK_ASYNC=1` 曾经同时打开两件事：**异步停放** 与 **checkpoint move**。
本机 async 的 stage 要求 `free >= want + 3 GiB`（want≈320 MiB，实际 free 0.8 GB）⇒ **永不分配**，
所以「省 92 ms」的收益全部来自 move，而异步那条路在本机一次都没跑过。

- 后果：一晚上的归因是错的（以为异步生效）。
- 修法：拆成 `STRATA_CKPT_MOVE_PARK`（P246），async 回退为只管异步。
- **教训**：合并的前提是「证明它们在同一验证单元」，不是「它们看起来都跟停放有关」。

## 5 以后加新开关时怎么做

1. 先测 **是否逐字节相同**（`STRATA_LOGPOS` 三次 dump 比 md5）：
   - 相同 ⇒ 考虑进 `*_DEFAULTS`（默认开，用户可 `*_DEFAULTS=0` 整体关）；
   - 不同 ⇒ 走第 2 步。
2. 再测 **是否与套装交互**（开套装 vs 套装+它，看是否可加）：
   - 不可加 ⇒ **并入 `GFX906_TUNED`**（第 8 项），**不要另起新套装** —— 两个套装会互相覆盖，组合爆炸；
   - 可加 ⇒ 独立 env。
3. 观测类永远独立，且**不设默认**（不要让它默认打开写日志）。

**不要做的事**：不要为了「配置看起来整齐」而把独立项塞进套装；也不要为了「方便一次关掉」而把套装拆成单点。
