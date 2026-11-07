# W930 · R69 结项：`#4590` penalty 窗口在我们这里**机制存在、症状不复现**

> 触发：队列第一条 R69（W919 立）。执行 2026-11-04 00:5x–01:2x，**零重启、零编译**，全程只发请求。

---

## 0 结论

| 项 | 结果 |
|---|---|
| 我们树有没有这个补丁 | **没有**（`penalty_counts_prompt` / `penalty_window_from` / `STRATA_PENALTY_PROMPT` 全 0；`penalty_rows` 19 处＝机制在，窗口起点不同） |
| 是否受 HIP 宏门控 | **否**（P257 那条规则不适用） |
| penalty 在我们部署里是否生效 | **取决于调用方**：默认（不传）关闭；**显式传则生效**（`pp=10` 实测明显改变输出） |
| 上游两个症状是否复现 | **都不复现**：抄错数字 0/9、返回旧答案 0/9 |
| 判决 | **DONE_NEG，不移植** |

---

## 1 补丁本身（`ed76b12f`，156 行）

改动 5 个文件，核心是 `include/strata/kernels/sampler.hpp` 里 12 行的两个 inline 函数：

```cpp
inline bool penalty_counts_prompt(const char* env) { return env != nullptr && env[0] == '1'; }
inline size_t penalty_window_from(size_t consumed_at_decode_start, bool counts_prompt) {
    return counts_prompt ? 0 : consumed_at_decode_start;
}
```

**注意：它不是 opt-in。** 默认就把窗口从「prompt + 回复」改成「只算回复」，`STRATA_PENALTY_PROMPT=1` 才恢复旧行为。移植过来会**改变默认采样**（在 penalty 开启时改数值）。

上游自报的机制：

> *"the prompt's own tokens (the digits of a new task, a quoted JSON answer) were penalised, and a conversation whose last turn asks for something new could get its previous answer back."*

实测数据：P100 / **IQ2_XS**，4 消息对话，32 seeds：旧 JSON 返回 **13/32 → 4/32**；R9700 / **IQ3_S**，16 seeds：**8/16 → 0/16**；61 题质量：**56/55（as shipped）→ 55（reply-only）→ 54（presence 0）**。

**注意最后一行**：reply-only 是 55，as shipped 是 56 和 55 —— **质量持平或略降**。它的价值是修正确性 bug，不是提升质量。

---

## 2 penalty 在我们部署里到底开不开 —— 三段证据

### 2.1 默认关闭（三重确认）

| 检查 | 结果 |
|---|---|
| `SamplerParams` 默认 | `penalty_last_n = 0`、`penalty_present = 0.0`（`sampler.hpp:21-24`） |
| 我们的 config | **无 `sampling` 块**（`sampling: null`） |
| `/props` 实测 | `{temperature: 1.0, top_p: 0.95, top_k: 20}` —— **无 presence_penalty** |
| 模型卡 `qwen4exp` | `thinking` 组**没有** presence_penalty；只有 `instruct` 组有 1.5 |

我们跑的是 **thinking** 模式（响应带 `reasoning_content`，`/props` 也是 thinking 组）⇒ **默认路径下 penalty 全程关闭**。

### 2.2 但显式传会生效（这条推翻了我最初"反正没开"的判断）

`presence_penalty` **不是**日志可见的（`keys` 拼进 prompt 文本，引擎解析后不打印），所以 `grep penalty_last_n → 0` **不能**当判据。改用极端值直接看行为：

```
prompt: "Repeat the word 'yes' twenty times"
instruct, pp=0   → "yes yes yes ..." ×20          finish=stop
instruct, pp=10  → 6 个 yes + "NOPE 😂👍(just kidding!)"   finish=length
```

**penalty 确实进了引擎。** ⇒ 任何传 `presence_penalty` 的客户端（含 web UI 切到 instruct 时模型卡注入的值）都会开这个窗口。

### 2.3 模型卡 instruct 的 1.5 是否自动注入 —— 测不出

`pp=1.5` 抑制不了那个 `yes` 重复（20 个照旧全出），因为 1.5 太弱而模型太固执。这个判据的分辨率不够，**记「未测出」**。

---

## 3 两个症状的复现测试（全部 instruct 模式，贪心）

### 3.1 抄写数字/十六进制串（高灵敏判据）

```
turn1: "The checksum field is 7F3A9C21DE4B ..."  →  "OK"
turn2: "Output the checksum again, exactly as given."
```

| presence_penalty | 正确 |
|---|---|
| 0.0 | **3/3** |
| 1.5（模型卡 instruct 值） | **3/3** |
| **10.0（远超正常，用于逼出机制）** | **3/3** |

即使 pp=10，12 位十六进制串一字不差。

### 3.2 新任务返回旧答案（上游的核心症状）

```
turn1: "Write a small JSON config for a service named alpha"  → JSON
turn2: "Different task now. Write a Python function add(a, b)"  → 应为 Python
```

| presence_penalty | 返回旧答案 |
|---|---|
| 0.0 | **0/3** |
| 1.5 | **0/3** |
| 10.0 | **0/3**（但输出崩坏：`defadd(aba+breturna+ba+a-a-bb-aa*bb/ab` —— penalty 过强的退化，不是旧答案） |

---

## 4 为什么我们不复现（判据不是"运气"）

上游的复现条件是 **P100 + IQ2_XS（2-bit）** 和 **R9700 + IQ3_S**，各 32/16 seeds。我们：

| 项 | 上游 | 我们 |
|---|---|---|
| 权重 | **IQ2_XS / IQ3_S**（2–3 bit） | **Q4_K / Q5_1**（4–5 bit） |
| 模型 | 同级但量化更狠 | Qwen3.8-Flash-Next |
| 采样 | 32 seeds（随机） | 贪心（temperature 0） |
| penalty 值 | 1.5 | 0 / 1.5 / **10** |

**差距的来源是模型有效能力，不是引擎逻辑。** penalty 确实在打 prompt 尾部的 token（`pp=10` 的输出崩坏证明了这一点），但 Q4_K 的模型有足够余量在被打压后仍选对答案；IQ2_XS 没有。

⇒ 这是一个**低精度场景的 bug**。

---

## 5 对 R74（W4A4）的一条警告

如果将来做 **W4A4**（激活降到 int4，R74），模型的有效精度会向 IQ2/IQ3 那一侧靠 —— 那时 **#4590 这类"低精度才显现"的正确性 bug 可能开始出现**。

⇒ 记档：**R74 若把 W4A4 推向生产，必须重跑本节的 3.1 / 3.2 两个测试**（成本很低，各 3×3 请求约 2 分钟，零重启）。这是 R74 之前没被列进判据的一条。

---

## 6 判决与账目

**R69 = DONE_NEG**，三条理由：

1. 机制存在但**症状不复现**（0/9 + 0/9，含 pp=10 的极端值）；
2. 移植会**改变默认采样行为**（非 opt-in），在 penalty 开启时改数值 —— 而我们连症状都没有，改了只有风险没有收益；
3. 上游自己也显示 reply-only **质量持平或略降**（56/55 → 55 → 54），它不是质量改进。

**保留的条件**（写进账本）：若出现以下任一情况，重测本节 3.1/3.2：
- 换更小的量化（IQ2/IQ3）或更小的模型；
- 把 W4A4 推向生产；
- 用户报告"新任务返回旧答案"。

---

## 7 生产状态

**零改动**：无重启、无编译、无 config 变更。只发了约 40 个请求（全部 instruct 短 prompt）。

| 项 | 值 |
|---|---|
| config | `51ef8837`（未变） |
| 引擎 | `a97f4479`（未变） |
| 健康 | `/health ok`、restarts=0 |

---

**【AUDIT24 口径注记】**
**灵敏度**：§75-101 的「0/9 + 0/9 不复现」是在**贪心 T=0** 下取的 3 次请求 = 确定性单样本，灵敏度远低于上游的 32 seeds。结论（症状不复现）成立，但"已证伪"的强度只到"本场景未观察到"。
