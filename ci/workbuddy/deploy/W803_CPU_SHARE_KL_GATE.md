# W803 `STRATA_PREFILL_CPU_SHARE` 质量门：六臂 teacher-forced KL（P23 翻案的收口）

日期 2026-10-25 23:28 ~ 2026-10-26 00:2x ｜ 引擎 0.1.49.2 / `0.2.4p4` ｜ MI50 32 GB (gfx906) ｜ pack `huihui-ud-iq4_xs`
｜ 臂 A/C = `share=0`（生产原值），B/D/E/F = `share=auto` ｜ 1,348 个配对评分位置

## 0 结论（先行）

1. **门通过，`STRATA_PREFILL_CPU_SHARE` 由 `0` 改为 `auto`，并显式钉 `MAX=1024`**（env 11 → 12 项）。
2. **判据不是「KL 小于某个绝对值」，而是「开与关的差 <= 开与开的差」** —— 因为这台机器上：
   - `share=0` 跑两遍（A 与 C，两次独立装载）**md5 完全相同**，KL 恰好 **0.000000**、argmax **100.00%** ⇒ 读数下限为零；
   - `share=auto` 跑四遍（B/D/E/F）**四个 md5 全不同** ⇒ 这个开关自己就让 prefill 逐次不同；
   - 于是「开 vs 关」的战绩（KL 均值 **0.00915 / 0.01090 / 0.01164 / 0.01481**）
     被「开 vs 开」的战绩（**0.00778 ~ 0.01134**，中位 0.00990）**完整包住**（0.00915 < 0.01134）。
3. 生产读数（同 bench，8K 会话）：**read 101 → 1,032 ms（原 1,476，-30.1%）**、
   **read 316 → 1,564 ms（原 2,453，-36.2%）**。
4. **代价照实写**：开 share 之后 **同一个请求两次可以给出不同字节**。我们因此失去「self = 0」的底噪，
   以后所有质量门必须每臂 n >= 2（见 §6 规则 X）。

## 1 这个门为什么不能照搬 W767 的做法

两个机制**互相排斥**，光靠参数调不出来：

| 机制 | 源码逐字 | 后果 |
|---|---|---|
| CPU share 只在 staged 的 prefill chunk 上生效 | `prefill.cpp:2882` `if (cpu_pool_ != nullptr && cpu_share_on() && !stream_all && !pipe_chunked)`；`stream_all = m.ring > STAGE && T >= stream_all_min()` | `T >= 1024`（钉 MAX=1024 时）的 chunk **完全不用 CPU** |
| LOGPOS 只在 verify 窗口上落行 | `generate.cpp:9543` "the teacher-forced log-probability of every token read here"；判定 `generate.cpp:12918` `if (no_short \|\| b - a > req_short_read) return false;` | fresh <= `--short-read` 的那一段走**解码窗口**，即**不经过 batched prefill** |

⇒ 「被 CPU 算过的 token」和「能被 LOGPOS 打分的 token」**不可能是同一批**。
所以本门采用**注入/测量分离**：

```
shape 轮（fresh ∈ (--short-read, 1024)）：走 staged batched prefill ⇒ CPU share 写进 KV
probe 轮（fresh <= --short-read）      ：走 verify 窗口       ⇒ LOGPOS 落行，读到的是被污染过的 KV
```

判的是**下游分布**：CPU 参与前若干轮 prefill 之后，模型的下一 token 分布有没有系统性移动。

参数：`--short-read 300`（只作仪器，**不在生产**）、`STRATA_LOGPOS_TOPK=64`、`STRATA_DBG_CPU_GATE=1`（只作臂自证）。

## 2 协议与自证（每条都是本车实测）

| 自证项 | 读数 |
|---|---|
| 臂身份 | 每臂从**容器内 `/proc/<pid>/environ`** 取，`ENVCHECK want=14 got=14` 六臂全过，并逐臂打印 `STRATA_PREFILL_CPU_SHARE=` 的值 |
| 输入同一 | 六臂 `corpus sha16` 相同；每臂 `prompt N tokens = R reused + F read` 逐轮可对 |
| 评分位置数 | 六臂全部 **1,376 行 / 1,348 个唯一 pos / 72 字段** ⇒ 同一段 token 序列被评分 |
| CPU 真的动了 | `cpu gate: … -> share` 行数：A/C = **0**，B/D/E/F = **326**（43 层 × 8 个 shape chunk 的一部分被 gate 拒） |
| 注入确实发生 | 两个注入前轮（t0/t1）四对 KL **全部恰好 0.000000**；t2 起才有非零 |
| 尺度 | 15 轮，shape chunk **551–617 token**（< 1024 ✓），probe **141–187 token**（<= 300 ✓），终态上下文 5,465 token |

## 3 结果

### 3.1 逐对

| 类型 | 对 | KL 均值 | KL 中位 | p90 | p99 | argmax 一致 | top-10 | KL=0 占比 |
|---|---|---|---|---|---|---|---|---|
| **off-vs-off** | A∥C | **0.000000** | 0.000000 | 0 | 0 | **100.00%** | 100.0% | **100.0%** |
| off-vs-on | A∥E | 0.009152 | 0.000000 | 0.0291 | 0.139 | 93.69% | 93.5% | 52.7% |
| off-vs-on | A∥F | 0.010902 | 0.000000 | 0.0345 | 0.258 | 92.95% | 93.7% | 50.1% |
| off-vs-on | A∥B | 0.011643 | 0.000000 | 0.0359 | 0.228 | 92.73% | 93.7% | 50.7% |
| off-vs-on | A∥D | **0.014812** | 0.000000 | 0.0409 | 0.293 | 92.43% | 93.6% | 49.9% |
| on-vs-on | E∥F | 0.009457 | 0.000000 | 0.0296 | 0.200 | 93.77% | 93.9% | 52.9% |
| on-vs-on | B∥E | **0.007781** | 0.000000 | 0.0243 | 0.187 | 93.69% | 94.1% | 53.5% |
| on-vs-on | B∥F | 0.009064 | 0.000000 | 0.0307 | 0.248 | 94.36% | 93.9% | 53.6% |
| on-vs-on | D∥E | 0.010350 | 0.000000 | 0.0319 | 0.224 | 93.40% | 93.9% | 53.1% |
| on-vs-on | D∥F | 0.011338 | 0.000000 | 0.0271 | 0.219 | 93.77% | 93.9% | 51.9% |
| on-vs-on | B∥D | 0.010700 | 0.000000 | 0.0349 | 0.237 | 93.25% | 93.8% | 51.7% |

（C 与 A 的 md5 相同，C∥X 与 A∥X 逐位相同，故不重复列。）

**判读**：

- **下限 0**：`share=0` 两次独立装载、两次独立 prefill，输出**逐字节相同**。所以任何一个非零数都是真信号，
  这一点比 W767 的 KV 车还干净（那车 self 也是 0，但只测了 decode 窗口）。
- **区间重叠**：off-vs-on 的 KL 均值范围 `[0.00915, 0.01481]`，on-vs-on 是 `[0.00778, 0.01134]`。
  前者最小值 **小于** 后者最大值 ⇒ **「开 share」与「关 share」的差，落在「share 跑两遍」的自身浮动之内**。
- 三个旁证同向：argmax 一致率重叠（92.4–93.7% vs 93.3–94.4%）、`KL=0` 占比重叠（49.9–52.7% vs 51.7–53.6%）、
  **中位数六臂全部为 0**（约一半的评分位置逐位相同）。
- 均值被少数「近平局」位置拉高：p99 在 0.14–0.29、max 0.57–3.15，而 **on-vs-on 的尾巴一样长**
  （p99 0.187–0.248、max 1.04–2.21）⇒ 尾巴不归给开关。

### 3.2 首注入后的第一个 token（上游 `DETAILS.md` 的 "first token" 口径）

`pos 1015` = 第一次 CPU 参与 prefill（t2，617 token）之后被评分的第一个位置：

| | A∥B | A∥D | A∥E | A∥F | B∥D | B∥E | B∥F | D∥E | D∥F | E∥F |
|---|---|---|---|---|---|---|---|---|---|---|
| KL | 0.01058 | 0.00568 | 0.00582 | 0.00628 | 0.00514 | 0.00947 | 0.01415 | 0.00111 | 0.01327 | 0.01507 |

off-vs-on `0.0057–0.0106` 仍在 on-vs-on `0.0011–0.0151` 之内。上游给的是「first token KL 0.002–0.0035（3060/A4000）」，同量级。

### 3.3 逐轮：没有累积漂移

每格 = A 对该 on 臂的平均 KL（该轮评分位置的均值）；"注入" = 该轮之前已经发生过几次 CPU share 的 prefill。

| 轮 | 类型 | 位置区间 | n | 注入 | A∥B | A∥D | A∥E | A∥F | 均值 |
|---|---|---|---|---|---|---|---|---|---|
| t0 | shape0→窗口 | 0–244 | 244 | 0 | 0 | 0 | 0 | 0 | **0.00000** |
| t1 | probe | 244–397 | 152 | 1 | 0 | 0 | 0 | 0 | **0.00000** |
| t2 | shape(仅 header 被评分) | 397–1020 | 5 | 1 | 0.02145 | 0.02224 | 0.01385 | 0.00574 | 0.01582 |
| t3 | probe | 1020–1207 | 186 | 2 | 0.00946 | 0.02226 | 0.01710 | 0.00634 | 0.01379 |
| t5 | probe | 1873–2028 | 154 | 3 | 0.01064 | 0.01225 | 0.02337 | 0.00788 | 0.01354 |
| t7 | probe | 2559–2678 | 118 | 4 | 0.01239 | 0.01990 | 0.00582 | 0.00675 | 0.01121 |
| t9 | probe | 3221–3400 | 178 | 5 | 0.00772 | 0.00680 | 0.00556 | 0.01305 | 0.00828 |
| t11 | probe | 4018–4159 | 140 | 6 | 0.01800 | 0.00943 | 0.00384 | 0.01305 | 0.01108 |
| t13 | probe | 4710–4853 | 142 | 7 | 0.04795 | 0.06291 | 0.02160 | 0.05131 | **0.04594** |

**t3→t11 平在 0.008–0.014，注入次数从 2 涨到 6 也没有放大** ⇒ 不累积。
`t13` 是唯一的高点（四个 on 臂一致地高，说明是那段文本本身更敏感，不是抽样），
但同一位置 on-vs-on 也有 0.019–0.029 量级 —— 仍不足以把开关判成「系统性偏移」。

### 3.4 标量（**不作判据**）

| 臂 | share | PPL | 自身 top1 命中 |
|---|---|---|---|
| A / C | 0 | 60.0268 / 60.0268 | 32.79% / 32.79% |
| B | auto | 59.2028 | 32.86% |
| D | auto | **57.6347** | 33.68% |
| E | auto | 59.1250 | 32.49% |
| F | auto | **60.7400** | 32.64% |

`share=auto` 自己的 PPL 跨度 **57.63–60.74（5.4%）**，比「开 vs 关」的差（1.4–4.0%）还大 ⇒
**PPL 在这个开关上没有分辨力**，与 W767 §2.6「标量同向单调但不可判」一致。
`d_lp(top)` 亦在 ±0.016 内摆动，符号在四对里不统一。

## 4 上游交叉核对（逐字，不是印象）

| 出处 | 逐字 | 与本车的关系 |
|---|---|---|
| `docs/DETAILS.md:1821` | "mean KL against the share off **0.004 (max 0.025)**"；"`STRATA_PREFILL_CPU_SHARE=0` turns it off and gives **0.1.40.3's exact bytes**" | 上游自报的量级与我们同阶（我们均值 0.009–0.015、median 0） |
| `docs/DETAILS.md:1891` 表 | CPU_SHARE 行 `0.0006-0.0007`，而上一行「the same engine run twice (the floor …)」也是 `0.0006-0.0007` | **上游也是拿「开关差」比「同配置两遍」**，正是本门 §3.1 的结构 |
| `prefill.cpp:196` | "`STRATA_PREFILL_CPU_SHARE=0` turns it off: the output is then the 0.1.40.3 bytes" | 我们的 A/C 就是这个「老字节」，且两次一致 |
| `prefill.cpp:184` | "0.1.41: **ON BY DEFAULT** where it was measured (CUDA builds …)", 512 tok −28…−34%、1,000 tok −20…−26% | **我们的 P23 把上游默认关掉了**，W802 的 −25% 本质是「恢复默认」 |
| `prefill.cpp:220` | `STRATA_PREFILL_CPU_SHARE_MAX` 缺省 **3072**（至少 1024）；且它被用作 `g_stream_min_share` ⇒ 抬高 `stream_all_min()` | 显式 `auto` 会把 1–3K 的 chunk 也改成 staged；**该区间本卡没测过 ⇒ 必须钉 1024**（P129） |
| `docs/DETAILS.md:1829` | "**0.1.42: not armed by default when memory is short.** A 0.1.41 report (RTX 5090 …) had chats failing and the engine restarting until `STRATA_PREFILL_CPU_SHARE=0` was set" | 显式 `auto` 只告警不关；本机六臂**日志无该 WARNING** ⇒ 内存门未触发（本机 arena 55.4 GiB 已 page-locked） |
| `docs/DETAILS.md:1821` | "The layer split, batch slots and **AMD (HIP) builds keep it off** unless you set the variable" | **上游对 HIP 不给默认值**；其理由是 RX 7900 GRE 上更慢（#1282），与质量无关 ⇒ 本卡是本项目第一个 HIP 质量读数 |
| 上游 issue **#3923**（open, 2026-10-24） | "CPU prefill share is still off by default and still **worth 2.9-3.4x prompt speed**" | 上游最新复核仍是「值得开」，但**只有速度、没有质量** |
| 上游 issue **#2685** 评论（RTX 4070 SUPER, sm_89） | "the run-to-run variation comes from the CPU share (on by default for chunks under 1,024 tokens, and **its split is timed per layer**)" | 与本车「on 四臂 md5 全不同」完全一致，且给出了机理 |

## 5 采纳与改动

| 项 | 前 | 后 |
|---|---|---|
| `STRATA_PREFILL_CPU_SHARE`（P23） | `0` | **`auto`** |
| `STRATA_PREFILL_CPU_SHARE_MAX`（P129，新） | 未设（显式 auto 时上游缺省 3072） | **`1024`**（保守钉住，见 §4 第 5 行） |
| config env 项数 | 11 | **12** |

生产复核：`verify_config` **PASS=36 FAIL=0**、`gen_config --live` **无差异**、
容器内 `/proc/<pid>/environ` **12 项**且 `CPU_SHARE=auto` / `MAX=1024` 逐字可读、`slots 9873` / `vram 668`。
回滚位 `data/strata-huihui-ud-iq4_xs.json.bak_w803_share`（改回一行 env 即可）。

**端到端冒烟**（同 `mt_chat` bench，8K 会话，两次连跑）：

| 轮 | read | 改前（W801 六臂中位，11 env） | 改后 RUN1 / RUN2 | Δ |
|---|---|---|---|---|
| T0 | 101 | 1,476 ms | **1,028.6 / 1,035.6** | **-30.1%** |
| T1 | 316 | 2,453 ms | **1,568.3 / 1,560.2** | **-36.2%** |

（改后第一次冒烟读数偏高 1,531/1,604/1,785/1,818，原因是**进程刚起、含首个 7,601-token BUILD**，
与「重启丢前两个请求」的旧记录一致；连跑两次即回到稳态。读 `read=5` 的两轮是会话缓存命中，不作比较。）

## 6 代价与新立的纪律

**代价（机制级，不可消除）**：`auto` 的份额是**按墙钟计时逐层测量**后分配的
（`prefill.cpp:190-193` "the share measured, each layer's CPU time per expert and the GPU's per streamed expert …as
running means"），所以**同一个请求在不同的运行里会被切成不同的样子** —— 本车 B/D/E/F 四个 md5 全不同即为实证。

**规则 X（质量门的底噪不再是 0）**：
`share=0` 时 self∥self 恰好为 0（A/C 的 md5 一致），**开了 share 就没有这个性质**。
⇒ 从此以后：
1. 任何质量门**每臂至少 n=2**，且必须报「同配置两遍」的底噪，不能拿一个绝对阈值（如 KL <= 0.01）当判据；
2. 判据写成「**变更臂 vs 基线臂 的差 <= 同配置两遍的差**」；
3. 需要「self = 0」的场合（例如查内核位一致），临时把 `STRATA_PREFILL_CPU_SHARE=0` 打回，事后恢复。

**与既有条目的一致性**：`W794` 早已记录「引擎跨请求不确定 ⇒ 禁哈希」。本车把这条**定位到具体来源**：
decode 侧的不确定源未定，但 **prefill 侧的不确定源之一就是这个 share**（`#2685` 的 4070S 评论独立复现了同一机制）。

## 7 限制（照实写）

1. **测的是下游分布，不是被 CPU 算过的那批 token**（§1 的机制排斥决定）。好在这正是用户能感知的量。
2. **一篇语料、一个 pack、一张卡、一个引擎版本**。语料是 `docs/*.md` 的英文散文句（904 句池，取前 202 句），
   不含代码/多语言/中文 —— 上游说「code/reasoning 的 KL 更低、chat 与非英文更高」，我们**没有覆盖那个更高的一档**。
3. **t2/t4/…/t14 这几个 shape 轮只有 4–5 个位置被评分**（只有 assistant header 进了窗口），
   所以「紧接在 share 之后」的读数样本很小；主样本来自 probe 轮的 118–186 个位置。
4. **`MAX=1024` 让 1–3K 的 chunk 回到全流式**，所以本门**没有覆盖** 1,024–3,072 这一段；那一段另立 P129。
5. **任务级门没做**：本车只到分布层。上游也没给任务级（#3923 只有速度）；W802 的 needle 32k 是 3/3 两臂相同，
   但 32k 是 >=1024 的 chunk，**不经过 share**，不能算这个开关的任务级证据。
6. `--short-read 300`、`STRATA_LOGPOS`、`STRATA_DBG_CPU_GATE` 都是仪器，**不在生产配置里**。

## 8 下一步（按收益/风险排）

1. **P129：`SHARE_MAX` 1024 vs 3072 vs 0，在本卡 read 1,500–2,500 上** —— 现在钉 1024 是保守值；
   上游在 5070 上 `3072` 于 2048 token「lost 2%」，但本卡 `wait copy` 在 1,588 token 只剩 57 ms（W800），
   也许根本不需要 staged。三臂、每臂 n>=3。
2. **任务级门**（唯一能回答「有没有变笨」）：短提示上的可判分小任务集（算术/抽取/排序，答案正则可验），
   greedy，A/B 各 20 题；判「答对数」而不是逐字相同。
3. **KPI-2 基线重定**：`W776 §13` 现在写的 TTFT 1.48/2.45/1.59/2.55 s 已作废，改成本车的
   1.03/1.56 s（read 101/316）。
4. **把 `share=auto` 当作新常量重跑一次 W802 的相位账**（`wait copy` 现在应该几乎消失），
   确认剩下的地板在哪 —— 否则下一轮会继续拿旧相位图找原因。

## 9 证据（自行打开）

| 件 | 说明 |
|---|---|
| `albus/w803/w803_logpos_{A,B,C,D,E,F}.tsv` | 六臂原始读数，各 1.4 MB / 1,376 行 / 72 字段（TOPK=64），1,348 个唯一 pos |
| `albus/w803/w803_kl_{A..F}.json` | 客户端记录（每轮 prompt_tokens / fresh / 墙钟） |
| `data/w803_kl_{232815,233820}.txt` | 驱动器全程（含 ENVCHECK、`cpu gate` 计数、`prompt N = R reused + F read`） |
| `albus/r5/mt_kl.py` · `kl_corpus.json` · `kl_probe.json` · `kl_pool.json` | 客户端 + 脚本化语料（904 句池） |
| `albus/r5/ab_p21.sh` | 驱动器（probe / full / extra 三种模式，`trap` 外的显式恢复 + 回滚位） |
| `albus/r5/kl_gate.py` · `kl_gate2.py` · `kl_gate3.py` | 三套分析器（全部配对 / 逐轮+首 token / 六臂按「对」抽样） |
| `albus/r5/_gh_cpushare.py` · `_gh_read.py` | 上游检索与正文读取（#3923 / #2685 / #2653 / #2478） |
