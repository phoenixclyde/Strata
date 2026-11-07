# W827 · 上游 v0.2.8 / 引擎 0.1.54 判定

> 2026-10-30 23:5x · 距上次判定（W820/W823，针对 0.1.52）已过 3 天，且中间我们已把生产升到 0.1.53
> 生产现状：`/data/bin/strata-0.1.53` · `--pack ud-q4_k_xl` · env 14 / args 33 · HEALTHY（容器已跑 22 h）

---

## 0 结论

**引擎：暂不升（DEFERRED）。理由不是"新版本不好"，而是「速度收益为 0、三条修复里两条不触发、一条只在重启时触发」。**

**但记一条硬约束**：`--spec > 4` 或 `--suffix-draft` 想超过 8 行窗口，**必须先升 0.2.8** —— 0.1.53 的窗口上限是 8。

---

## 1 上游到哪了

| 对象 | 版本 | 时间 |
|---|---|---|
| app / Control | **0.2.8**（Control 0.1.54） | 2026-10-29 22:40 UTC（= 今天 06:40） |
| Qwen 引擎 | **0.1.54** | 同上；我们在 **0.1.53** |
| 发布正文 | 9,764 字符（比 0.2.7 的 30,567 短很多） | — |

仍然**没有 gfx906 的预编译包**（14 个 Qwen 包里 AMD 只有 rx6000/rx7900/rx9070 等），每次升级都得自建。

---

## 2 引擎面的实质改动：42 个文件，核心只有一件事

`v0.2.7.1 → v0.2.8`：70 提交 / 148 文件，其中引擎面（`src/`+`include/`+`CMakeLists`）**42 个**。

改动最大的是 **verify 窗口从 8 行放到 16 行**（HIP 独占）：

| 文件 | 改了什么 |
|---|---|
| `include/strata/kernels/window_limits.hpp`（**新增**） | 定义 `STRATA_VERIFY_MAX_T`（8 或 16），并写明规则 |
| `src/kernels/cuda/s2_expert_grouped.cu` +72/−20 | 一个专家的 group 超过 `GMAX=8` 条目时分**两趟**跑（`SKIP=GMAX`），逐位等价 |
| `src/core/expert_source.cpp` +80 | `kMaxWindowEntries` 128→256（**仅 16 行窗口时**）；`n_tok` 上限改为 `kWindowMaxT` |
| `src/core/verify.cpp` +28/−50 | `max_t` 检查、`have[]` 宽度改为 `kWindowMaxT+1` |
| `src/kernels/cuda/verify_kernels.cu` +45 | 模板默认值改 `kVerifyNarrowT`；`resident_plan` 按窗口类别选 128/256 线程 |

**决定性的一句话**（`window_limits.hpp` 逐字）：

> a window of up to `kVerifyNarrowT` (8) rows runs **EXACTLY the code it ran at 8**
> (the same kernel instantiations, the same buffer sizes); the wider code is reached **only by a window of 9..16 rows**.

⇒ **窗口 ≤ 8 行时，0.1.54 的这 42 个文件对我们的产物逐位等价、零速度变化。**

---

## 3 逐条对照我们的实际用法

| 0.2.8 的改动 | 我们会不会碰到 | 判断依据 |
|---|---|---|
| **16 行 verify 窗口**（HIP） | **不会** | `--spec 4`，`--suffix-draft` 未设（默认 3，最多长到 8）⇒ 窗口 5–8 行，走窄路径 |
| **四卡 R9700 profile** | 不会 | 单卡 |
| **Arc B 系列双卡**（decode +17~23%） | 不会 | AMD gfx906 |
| **#4420 park 保留共享前缀**（5K 前缀 4130→323 ms） | **不会** | `--batch` **未设** ⇒ 不 park slot |
| **#4518 PLE 表锁定时对话缓存不再短缺** | **不会** | 我们的 PLE **没锁住**（`ulimit -l=8 MB`，`mlock` ENOMEM） |
| **#4474 自动专家缓存保留你要求的 reserve** | **可能会** | 我们用 `--expert-cache auto` + `STRATA_RESIDENT_HEADROOM_GIB=0.5` |
| **#4051 新引擎等旧引擎释放内存** | **会**（重启时） | 我们重启频繁；**W828 那次**（10-31）MMQ 臂启动就撞过 `memory guard: current 105.4 GiB, available 20.3 GiB`（原文写"W826 那次"，时序不可能 —— W827 写于 10-30 23:49，AUDIT12 P2-11） |
| **工具调用容错**（98.3% vs 92.9%，1,462 轮） | **看用法** | 在 `serve/frontend.py +242` / `serve/server.py +77`，属 **server 层**，不是引擎 |
| 其余（DeepSeek、Mac、NVIDIA、Monitor、Terminal） | 不会 | 平台/引擎无关 |

**净结果**：能命中的只有 **#4474（reserve）与 #4051（重启内存）** —— 两条都**不是每天跑在关键路径上**；
工具调用容错在 server 层，是唯一有"日常体感"的收益。

---

## 4 为什么"发布说明里的 +8.1% decode"不能用在我们身上

正文里「0.2.8 vs 0.2.7.1，五对配对」给出 R9700 单卡 decode **73.7 → 79.7（story，+8.1%）**、106.3 → 107.8（code），
prompt 不变（<0.4%）。

这个数是**综合结果**，而本版对 AMD 的引擎改动**只有 16 行窗口那一项**（其余是 DeepSeek/Mac/Arc/四卡 profile）。
我们 `--spec 4` 走窄路径 ⇒ 拿不到这 +8.1%。

**旁证**：正文自己写"One request alone runs at the same speed as before (67 tokens per second)"（四卡 profile 段），
说明单请求路径确实没变。

---

## 5 什么时候必须升（触发条件，写死）

满足任一条就升，**不再逐次评估**：

1. **想把 `--spec` 提到 5 以上，或让 `--suffix-draft` 的窗口超过 8 行** —— 0.1.53 会直接拒（`max_t > kVerifyMaxT`）。
2. **想开 `--batch` / `--parallel`（多并发）** —— 那时 #4420 会命中，且需要 16 行窗口承接更大批。
3. 上游出现 **gfx906 相关的**速度或正确性修复（本版没有）。
4. 出现我们实际踩到的、且只在本版修的问题（如 #4051 的内存竞争真的把重启搞坏）。

---

## 6 一个容易被忽略的耦合：`calibrate` 与引擎版本

昨晚定的 P0（`tools/calibrate.py` 标定 5 类参数）**依赖引擎版本**：

- 它要启动引擎、跑真实的 prefill/decode；
- 若先升 0.2.8 再标定，标定结果就是新引擎的；
- 若先在 0.1.53 上标定、之后又升 0.2.8，**标定要重跑**（`--spec-min-p`、`--adapt-*` 都跟引擎的 verify/缓存行为相关）。

⇒ **顺序要先定死**：**先决定升不升引擎，再跑 calibrate。** 本判定为"暂不升"，所以 **P0 可以直接在 0.1.53 上跑**，不必等。

反过来，如果将来决定升，calibrate 必须重跑 —— 这一点要写进触发条件 1/2 的执行清单里。

---

## 7 与 0.1.53 那次升级的差别（为什么上次升、这次不升）

| | 0.1.49.2 → 0.1.53（W824，升了） | 0.1.53 → 0.1.54（本版，暂不升） |
|---|---|---|
| 修的问题 | **#3602 PLE reader 挂死**、**#1503 会话 KV 串用** | #4420 park 丢前缀、#4474 reserve、#4051 重启内存 |
| 性质 | **会挂死 / 会串数据** | 变慢、少用一点内存、重启偶发竞争 |
| 是否命中我们的用法 | 命中（PLE 我们开、多会话我们有） | **两条不命中**（无 `--batch`、PLE 未锁） |
| 速度收益 | 0（已验证） | 0（本版可证：窄窗口逐位等价） |

⇒ 判据一致：**命中高频路径的严重缺陷才升，否则攒着。**

---

## 8 数据出处

- release 正文：`albus/w827/v0.2.8.md`（9,764 B，全文已落盘）
- 引擎面文件清单：`albus/w827/eng_files.json`（42 个）
- 对照件：`albus/w827/up/`（`s2_expert_grouped.cu`、`window_limits.hpp`、`conversation_cache.hpp`、`expert_source.cpp`、`verify.cpp`、`verify_kernels.cu` 的两版）
- 脚本：`albus/w827/{diff_win,diff_key}.py`
- 上游关键引文：`window_limits.hpp` 的"EXACTLY the code it ran at 8"；`conversation_cache.hpp` 的
  "#4420, 0.2.6 -> 0.2.7: 323 ms -> 4130 ms for a 5 K-token prefix"

## 9 事后注记（AUDIT12，2026-10-31）

本节"暂不升（DEFERRED）"在 **约 2 小时后被推翻**：W828 把生产升到了 0.1.54。
§5 列的四条触发条件当时 **一条也没满足**（`--spec` 仍 4、无 `--batch`、无 gfx906 修复、#4051 未真炸），
所以这次是**决策反转（用户要求"升上游最新"）**，不是条件触发。留此注记，避免单看本文误以为"按条件升级"。
另：本文 §3 称 `#4420`/`#4518` 不命中、`#4474`/`#4051` 命中，其中 #4474 的"槽位 −85"后来实测为 **−88**（22.04→21.79 GiB），方向一致。
