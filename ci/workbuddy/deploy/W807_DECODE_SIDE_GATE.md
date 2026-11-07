# W807 · 解码侧质量仪器：造出来、校准、并一次结清三笔债

日期：2026-10-26 21:03-22:0x ｜ 生产：`strata166-407` / `strata-gfx906:0.2.4p4` / 引擎 0.1.49.2 / env 12 项
结论先行：**解码侧现在有仪器了，底噪是 0**；三笔一直挂着的解码侧质量债当场结清——
`RT_SKIP` 与 `attn swizzle` 都会改文本但**一分准确率不掉**，`GDN_HEAD/PP` 是**逐位等价**的替换。

---

## 0 三条结论

1. **仪器成立**：6 条 prompt × 约 520 token 的贪心生成，**同配置两遍 6/6 逐字相同**（底噪 0）；
   而开关一改就 4-6 条分叉。⇒ 它有分辨力，而且比上游的底噪（KL 0.0006-0.0007）还干净。
2. **发散不等于变坏**：`RT_SKIP` 6/6 分叉，但 36 题任务门 **A/A2/B 三臂按值全 34/36、错同两题、配对不一致 0/36**。
   `attn swizzle` 4/6 分叉，任务门同样 **三臂全 34/36、0/36 不一致**。
3. **`GDN_HEAD` + `GDN_PP` 是逐位等价**：摘掉它们，6 条 × 约 520 token 的输出**逐字相同**。
   ⇒ 这两个当初就不需要质量门（它们只换 kernel，不改算术），现在有实测背书。

---

## 1 为什么必须换仪器：`LOGPOS` 看不到解码

`STRATA_LOGPOS` 在整个引擎里只有**一个**写点：`generate.cpp:13084`，在 `read_windows`（**提示**读入的窗口循环）里。
它逐行写的是「本窗口第 t 个位置的 teacher-forced log-probability」，`targets[t] = nxt[t]` 是提示自己的下一个 token。
生成阶段的 verify 窗口**从不**调用它 ⇒ **这套门只量提示侧**。

这解释了 `W806` 那三个「逐字节相同」：三个解码侧开关不是没效果，是仪器看不见。

`RT_SKIP` 的触发条件也解释了为什么它在**提示**的窗口里几乎不触发（`expert_source.cpp:4853-4862` 逐字）：

> a missed expert that **EVERY token of the window** routes only at rank >= R (the smallest weights of the top-10) is neither copied
> nor computed; its contribution is zero, without renormalisation (the others keep the weight the router gave them).

窗口里每个 token 都要把该缺失专家排在 >=7 位。窗口 1-2 个 token 时这很容易；窗口 60-190 个 token 时近乎不可能
——而 `read_windows` 的窗口是 `min(S, b-q)`，正是几十上百。生产日志里 `31109 / 32256`（**96.4%**）的缺失专家被跳过，
那是**解码**窗口的成绩。

---

## 2 上游怎么测解码路径（逐字读了 `docs/DETAILS.md`）

`DETAILS.md:1880`：

> **Answers differ slightly from 0.1.41** (`STRATA_ROUTE_TAIL_SKIP=0` brings them back). Teacher-forced KL of the decode path
> (the default's own greedy text and the default sampled at T=0.8, 28 chat prompts of code, reasoning, chat, six languages and
> long-document summaries, 220 tokens each, about 6,000 scored tokens per set, **through the real verify windows with the MTP drafts**)

| 上游读数（`:1885-1890`） | RTX 3060 12 GB IQ3_XXS | RTX A4000 16 GB Q2_0 |
|---|---|---|
| KL（0.1.41 ∥ tail skip），均值，贪心 / 采样 | 0.0058 / 0.0056 | 0.0032 / 0.0030 |
| p99 / max（贪心） | 0.061 / 0.29 | 0.035 / 0.32 |
| **top-1 一致率** | **97.7% / 97.5%** | **98.2% / 98.2%** |
| 同一引擎跑两遍（底噪） | 0.0006-0.0007 | 0.0007 |

任务级（`:1895`）：HumanEval 取偶数题 82 + 30 道生成推理题，`76/78、27/27` 对 `78/82、29`，原文逐字
"**The runs do not separate the settings** (one run each; a change of 3 reasoning tasks is noise)"。

⇒ 上游的立场很清楚：**它确实改答案，但量在「每 token 百分之几」，任务级看不出来，所以默认开**（CUDA 上 +15.6% decode）。
另外它有一条我们正好不在其中的豁免：`DETAILS.md:1873` "when 90% or more of all the experts are in the GPU cache: the few misses are
cheap there and the skip costs more draft acceptance than it saves"。**我们常驻只有 40%**，正是它设计要生效的区间
（实测 96.4% 的缺失专家被跳过）。

我们不打算为了这件事重建镜像去插 LOGPOS 钩子——**用「贪心输出逐字比对 + 任务准确率」两层，就能拿到同一个判断**，
而且第一层还更便宜、底噪更低。

---

## 3 仪器设计（三条口径，写在驱动器的头注释里）

| 项 | 设定 | 为什么 |
|---|---|---|
| 生成 | 6 条 prompt（工程/推理/说明文，各要求 ~400 词），`max_tokens 600`、`temperature 0`、`top_p 1`、`reasoning_effort none` | 贪心 ⇒ 同配置必须给出同一串 token；长度足够让"每 token 2% 的分歧"必然显形 |
| 确定性 | 全部臂 `STRATA_PREFILL_CPU_SHARE=0` | `W803` 已证 share=0 时 prefill 逐字节确定 ⇒ 任何分叉只能来自被测量的解码侧开关 |
| 路径隔离 | 全部臂 `--short-read 0` | 强制 prompt 走 batched prefill，不经窗口（否则提示侧的窗口也会贡献差异） |
| 底噪 | **A 与 A2 是同一份配置的两次装载** | 不设底噪就没法判断"6/6 分叉"意味着什么 |
| 判据 | 第一层「会不会变」；第二层「变好还是变坏」= 36 题任务门（判答对，不判逐字） | 单看发散会把所有改答案的开关一律判死，那等于禁止任何数值优化 |

臂（五条）：**A** = 生产解码器（`RT_SKIP=7` 等）｜**A2** = A 重复｜**B** = `RT_SKIP=0`｜**C** = 摘 `GDN_HEAD`+`GDN_PP`｜**D** = 摘 `GFX906_ATTN_QUERY_SWIZZLE`。

---

## 4 数据

### 4.1 底噪与发散（字符级首个分歧点，括号内按实测 5.90 字符/token 换算）

| prompt | 生成 token | A∥A2（底噪） | B（`RT_SKIP=0`） | C（GDN 摘掉） | D（swizzle 摘掉） |
|---|---|---|---|---|---|
| p0 | 544 | **逐字相同** | 409（≈73 tok） | 逐字相同 | 逐字相同（>=545 内未分叉） |
| p1 | 551 | **逐字相同** | 1249（≈205） | 逐字相同 | 逐字相同（>=551 内未分叉） |
| p2 | 479 | **逐字相同** | 207（≈35） | 逐字相同 | 2511（≈429） |
| p3 | 514 | **逐字相同** | 472（≈79） | 逐字相同 | 194（≈33） |
| p4 | 536 | **逐字相同** | 414（≈69） | 逐字相同 | 125（≈21） |
| p5 | 541 | **逐字相同** | 88（≈15） | 逐字相同 | 61（≈10） |

| | 分叉条数 | 分叉点（token，未分叉按观测长度封顶） | 隐含 per-token argmax 一致率 |
|---|---|---|---|
| **A∥A2（底噪）** | **0/6** | — | **100%** |
| A∥B（`RT_SKIP` 7→0） | **6/6** | 15 / 35 / 69 / 73 / 79 / 205，**中位 71** | **≈98.6%** |
| A∥C（GDN 摘掉） | **0/6** | — | **100%（逐位等价）** |
| A∥D（swizzle 摘掉） | **4/6** | 10 / 21 / 33 / 429（另 2 条在 545/551 内未分叉），**中位 27** | **≈96.3%** |

> **【AUDIT10 更正 2026-10-26 23:3x】上一行原来写「中位 ≈231 / ≈99.6%」，错了。**
> 错因：把 2 条**删失**观测（551 token 内没分叉）当成 545 / 551 这两个「观测值」一起取中位。
> 删失样本不能当事件（规则 Y）。四个真实分歧点的中位是 **(21+33)/2 = 27** ⇒ 一致率 **1−1/27 = 96.3%**。
> ⇒ 与 `RT_SKIP`（6/6、中位 71 → 98.6%）相比，**swizzle 分叉得更早，不是更晚**；
> 本文原来那句按扰动强度排的「`RT_SKIP` > `attn swizzle` > `GDN`」**方向反了**，
> 正确是 **swizzle（27，4/6+2 删失）> RT_SKIP（71，6/6）> GDN（0/6，成对 bitwise）**。
> 任务门那一层（三臂 34/36、同错 t21/t32、不一致 0）已由 `AUDIT10` 复算确认，所以 `P110` 的采纳不变。

**与上游对账**：上游独立测得 `RT_SKIP` 的 top-1 一致率 **97.7% / 98.2%**（约 6,000 个打分 token），
我们这套廉价近似给出 **≈98.6%**（6 条 × 520 token，n 小得多）——同一档。两个互不相同的仪器给出一致的量级，
这比单独一条更有说服力。

### 4.2 第二层：任务级门（36 题，判答对）

| 门 | A（生产） | A2（重复） | B（改） | 配对不一致 |
|---|---|---|---|---|
| `RT_SKIP` 7 → 0 | 34/36 | 34/36 | **34/36** | **A∥B = 0/36** |
| `attn swizzle` 开 → 关 | 34/36 | 34/36 | **34/36** | **A∥B = 0/36** |

两套门里，三臂错的都是**同两题**（t21 应 4403 全答 4423；t32 应 17 全答 14）——那是模型能力，与本轮开关无关。
（`RT_SKIP` 那组的 B 臂在**严格**口径下少 1 题：t04 答成裸 `12`、值正确但没有 `ANSWER:` 前缀；按值同分。）

---

## 5 三笔债的处置

| 债 | 之前的状态 | 现在的读数 | 处置 |
|---|---|---|---|
| **`P127`（`RT_SKIP=7`）** | 「按设计改答案，KL 0.003-0.006，量级=量化误差，**需一次 LOGPOS 门**」（`W800` 挂的账） | 贪心文本 6/6 分叉（中位第 71 个 token）→ 隐含 top-1 ≈98.6%；**任务门 0/36 不一致**；跳过率 96.4% | **债清，维持 ADOPTED**。原挂账写法（"要一次 LOGPOS 门"）作废——LOGPOS 测不了它，改记本仪器的两层读数 |
| **`P110`（attn swizzle）** | 采纳 -1.6%，只知道「不是 bitwise 相同」 | 4/6 分叉（**中位 27** token → **≈96.3%**，比 `RT_SKIP` 更早分叉），**任务门 0/36 不一致** | **债清，维持 ADOPTED**；但它**不是**逐位等价，而且**扰动比 `RT_SKIP` 更强**，以后动 attention 时别把两者混为一谈 |
| **`P115/P116`（`GDN_HEAD`+`GDN_PP`）** | 采纳 -2.6%，无质量数据 | **6/6 逐字相同（≈3,100 token 全等）** | **债清**：这是 bitwise 等价的 kernel 替换，质量代价 = 0 |

---

## 6 局限（照实写，别把结论用过头）

1. **这不是 KL**。贪心发散只给「第一处不同的位置」，隐含一致率是**由几何分布反推的近似**（`p ≈ 1 - 1/中位`），
   n=6 条 prompt，置信区间很宽。它够用来排序和设量级，不够用来写"KL = x"。
2. **只测贪心**。`temperature 0.8` 的采样路径没测；上游两者都测（0.0058 vs 0.0056，几乎相同），所以这条大概率不改变结论。
3. **36 题的分辨率是 1/36 = 2.8 pp**，比上游自认的噪声阈（3/30 = 10 pp）细，但仍测不出「1-2 题的差别」。
4. **`--short-read 0` 与 `share=0` 是刻意的隔离**，不是生产配置。生产里 `share=auto` 本身就会让 prefill 逐次不同
   （`W803` 规则 X），所以生产中的实际发散**比这里更大**——本仪器量的是"这个解码开关自带多少"，这正是我们要的。
5. `GDN` 的"逐位等价"只在**这条语料 + 这条路径**上验证过（6 条 × 520 token，T<=600）。更长的上下文、
   别的 batch 形状里理论上是同一个 kernel，但没测。

---

## 7 生产状态与证据

| 项 | 读数 |
|---|---|
| 镜像 / 引擎 | `0.2.4p4` / 0.1.49.2（二进制 md5 `184f8ade…`，未被本轮改动） |
| 配置 | env **12 项**，`RT_SKIP=7`、`CPU_SHARE=auto`、`CPU_SHARE_MAX=3072`、`--prefill auto`、无 `--short-read` |

证据（自己点开）：

| 件 | 说明 |
|---|---|
| `albus/w807/w807_decq_{A,A2,B,C,D}.json` | 五臂的完整生成文本（各 6 条，约 3,000 字符/条） |
| `albus/w807/w807b_task_{A,A2,B}.json` | `RT_SKIP` 任务门逐题原文（含 `got`/`expect`） |
| `albus/w807/w807c_task_{A,A2,B}.json` | `attn swizzle` 任务门逐题原文 |
| `albus/r5/{ab_p32,ab_p33,ab_p34}.sh` · `mt_decq.py` · `dec_gate.py` · `dec_corpus.json` | 驱动器 / 客户端 / 分析器 / 语料 |
| `/data/w807_dec_*.txt` · `w807b_task_*.txt` · `w807c_task_*.txt`（166 上） | 三车门全程（含 CFGCHECK/ENVCHECK/每臂 tail_skip 计数） |
