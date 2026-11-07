# W805 相位账补到真实 chunk（8192 档）+ 上游 gfx906 的三条新线索

日期 2026-10-26 19:19~20:0x ｜ 引擎 0.1.49.2 / `0.2.4p4` ｜ MI50 32 GB (gfx906) ｜ pack `huihui-ud-iq4_xs`

## 0 结论（先行）

1. **拷贝问题已经彻底关掉**：在真实使用的 8192 档（`stream_all`）上 `wait copy` 只剩 **0.4-0.9%**。
   `W800` 那张「754 ms / 23.5%」的图属于 `share=0` 与「小 chunk」的组合，现在两头都不成立了。
2. **新的结构性事实：`qsa attn` 随 read 上升**（7.7% / 10.7% / **14.5%** 于 1.9K / 3.3K / 6.2K），
   而 `gemm gate/up` 相对下降（22.7% / 22.1% / 20.6%）。
   **【AUDIT10 更正】原句「大 read 的敌人是 attention」要改**：补上 `ple` 之后，6.2K 档的顺序是
   gate/up 20.6% > **ple 15.4%** > attn 14.5% ⇒ **attention 并不独特，`ple` 与它同档**。
   正确表述：**小 read 的敌人是 dense + MoE（gate/up + down + qsa proj ≈ 35%）；
   大 read 变贵的是 attention 与 PLE 两件事，而不是只有 attention。**
3. **chunk 尺寸 8192 -> 16384：28,878-token prompt 上中位 -4.4%（40.2-43.6 s vs 44.0-45.6 s，两臂区间不重叠，
   正反两种顺序各测一次）**。代价：prompt 缓冲借走的 cache 槽从 4.43 GiB 涨到 7.43 GiB。
4. **上游有两条直接对口的 gfx906 线索**（都需重建镜像才谈得上测）：
   - **`STRATA_PF_MMVQ`（#4157 / draft PR #4158）**：小 chunk 的 dense 投影改用解码路径的 native MMVQ，
     上游 MI50 实测 **164-166 token 的轮次 1.88/1.78 s -> 1.59/1.54 s（-15%）**，正好是我们 KPI-2 的主区间；
   - **`#4156`**：gfx906 的 HIP 兼容层 stream-priority 映射，是上面那条的**编译前置**。
5. **一位独立 MI50 用户（#4159）复现了我们的两个采纳**：`STRATA_HIP_PROMPT_F16=1` + CPU share 在 16k prompt 上
   393 -> **498 tok/s（+27%）**，118k 上 363 -> 468（+29%）。他的质量门还给了我们一把标尺（见 §3.4）。
6. **纠正一条旧结论**：`W800` 记的「无任何 `restored` 行 ⇒ resume 一律来自热批槽」**已过时**。
   现在的日志里有 **283 条 `conversation cache: restored`**，实测 **43,796 tok/s** 的等效恢复速度（见 §6）。

## 1 相位账补到真实 chunk

一个臂（生产配置 `auto` + `MAX=3072`），只加 `STRATA_PREFILL_TIMING=1`；单发 fresh prompt，每档两次：

| read | GPU timeline | gemm gate/up | **ple** | qsa attn | gdn | gemm down | hc read | dequant | router+shared | qsa proj | wait copy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1,881 | 3,775 ms | **22.7%** | **10.4%** | 7.7% | 8.6% | 10.9% | 8.4% | 6.1% | 8.0% | 4.0% | 0.9% |
| 3,313 | 6,474 ms | **22.1%** | **14.4%** | 10.7% | 10.8% | 10.6% | 6.7% | 8.5% | 2.5% | 4.1% | 0.7% |
| 6,152 | 10,477 ms | **20.6%** | **15.4%** | 14.5% | 10.2% | 9.9% | 7.2% | 4.9% | 2.5% | 4.5% | 0.4% |

> **【AUDIT10 更正 2026-10-26 23:2x】上表补了 `ple` 这一列**（原文漏了）。PH 行的字段本身是自洽的——
> 逐档加总 3,774 / 6,474 / 10,476 ms，与 `GPU timeline` 差 0-1 ms——但原文只挑了 7-9 项，
> **漏掉的 `ple` 在 3.3K 与 6.2K 档是第二大项（14.4% / 15.4%）**，比 `qsa attn` 还大。
> 仍然没列的：`gdn out proj`（3.2/3.5/3.8%）、`gdn recurrence`（2.8/2.8/3.1%）、`embed+steps`、`host grouping`（2.7%）、
> `hc write`、`combine`、`gather`、`qsa select`、`qsa indexer`。完整字段见 `AUDIT10 §2 P1-3`。
> **`ple` 是什么**：从第 1 层起等 SSD 读完 PLE（n-gram 表）行，源码逐字 "the PLE rows, read from layer 1 on
> (a wait for the SSD read …)"。生产用的是 `--ple-io` 的默认 `direct`（无缓冲 SSD 读），
> 而 `direct|mmap|ram` 三个值都在本树（`generate.cpp:806`）——**这是下一轮的第一顺位**（§4 已列）。

**每 1,000 token 的绝对成本**（把百分比还原成 ms）：

| read | gemm gate/up | qsa attn | ple |
|---|---|---|---|
| 1,881 | 456 ms | 155 ms | 209 ms |
| 3,313 | 431 ms | 209 ms | 281 ms |
| 6,152 | **351 ms** | **247 ms** | 263 ms |

⇒ 两条曲线方向相反：**gate/up 随 chunk 变大而变便宜（456 -> 351），attention 变贵（155 -> 247）**。
交叉点在 4-5K 附近。这解释了为什么「chunk 越大越好」在 6K 已经不成立 —— 到了 8192 档，attention 是增长项。

`qsa indexer` 0.0%、`qsa select` 0.1-0.4%。这两个数字很关键：上游 #4119 那个「两遍 QSA 选择」的优化
（256K prompt 上 +5.2%）**打的是 `qsa select`**，而我们在 gfx906 上这一项本来就几乎为零 ⇒ **与本卡无关，直接排除**。

## 2 chunk 尺寸：8192 vs 16384

**机理（源码逐字）**：`stream_all` 时「一个 chunk 会把每个专家读一遍」，所以
**chunk 数就是成本单位** —— `prefill.cpp:7459`「a prompt's cost is its number of such chunks」、
`generate.cpp:7448`（#2824）「a single pass reads each expert once … splitting it would only add a pass」。
§1 的每 1k 成本同向。`--prefill auto:16384` 是现成的旋钮（`generate.cpp:2560` 解析 `auto:N`）。

同一个 **28,878-token** prompt，正反两种顺序各跑一次（每臂 1-2 次）：

| 臂 | 第 1 次（重启后首个请求） | 第 2 次 | 第 3 次 | 中位 |
|---|---|---|---|---|
| **A = `auto`（8192）** | 45,551 ms（634 tok/s） | 43,963 ms（658） | 45,429 ms（636） | **45,429 ms** |
| **B = `auto:16384`** | 43,446 ms（665） | 40,155 ms（**720**） | 43,632 ms（662） | **43,446 ms** |

**两臂区间不重叠**（B 最大 43,632 < A 最小 43,963）⇒ 中位 **-4.4%**，最好一次 **-8.7%**。
顺序效应也在数据里：每臂「重启后首个请求」比同臂第二次慢约 1.5 s（A 45.6/45.4 vs 44.0；B 43.4/43.6 vs 40.2），
所以只跑一遍会把它误读成臂间差 —— 这正是要正反各跑一次的原因。

**开关自证**（不是靠命令行自报，而是从启动块里读）：
`prompt chunk auto: 16384 tokens, a 384-slot ring` + `the prompt path borrows 3299 CUDA0 cache slots (7.43 GiB)`，
对照臂是 `8192 tokens` + `1969 slots (4.43 GiB)`。**代价就是这 +3 GiB 的 cache 借用**（prompt 读完会还回去）。

## 3 上游检索（逐条读正文，不猜）

| 条目 | 内容 | 对我们是 |
|---|---|---|
| **#4159**（issue，10-25） | 独立 MI50 用户：`STRATA_HIP_PROMPT_F16=1` + CPU share 在 16k prompt 上 393 -> **498 tok/s（+27%）**，118k 上 363 -> 468（+29%）；agent 轮次 91/165/480/1300/3500 fresh token 全部大幅缩短 | **复现了我们的两个采纳**（P103 + P23）；`STRATA_RDNA2_SGEMM=all` 352（更差）、`STRATA_EXP_MODE=2` 469（更差）⇒ 这两条不用再试 |
| **#4157 + #4158**（10-25） | gfx906 小 chunk 的 **dense 投影**改用 native MMVQ（`STRATA_PF_MMVQ=1`，阈值 256）；170-token chunk 里 **930/1730 ms** 花在 hc read / gdn / qsa proj / gdn out proj；164-166 token 轮次 **1.88/1.78 -> 1.59/1.54 s（-15%）**；阈值 512/2048 会拖慢更大的 chunk | **最高价值的未落地项**，已登记 `P130`（CANDIDATE，需重建） |
| **#4156**（PR，10-25） | gfx906 的 HIP 兼容层 stream-priority 映射 | 上面那条的**编译前置**，重建时必须一起摘 |
| **#4119**（PR，10-25） | 两遍 QSA prompt selection（3xTF32 只在 top-k 切点附近），打的是 **`qsa select`** | **排除**：我们 `qsa select` 只占 0.1-0.4%（§1） |
| **#4206**（issue，10-26） | `--prompt-cache-every` 在 N 小于 chunk 时被 clamp、纯 append 仍整段重读 | **不适用**：我们 N=8192 = chunk 8192，且实测 restore 在工作（§6） |

### 3.4 他给的还有一个质量标尺

#4159 / #4157 用的是同一个 harness：**只把 chunk 尺寸从 512 改成 1024（纯重排、不改任何开关）=> mean KL 0.052**，
而 `STRATA_PF_MMVQ` 是 **0.065**、CPU share 是 **0.051**、F16 是 **0.049** —— 作者据此写「sits at the level of a pure
reordering of the prefix's sums」。

**这把尺子对我们有用**：我们在 `W803`/`W804` 上量到的两个采纳开关是 **0.008-0.030**，**低于**这个「纯重排」参照。
⇒ 我们的 KL 判据（规则 X：变更 vs 同配置两遍）比「和纯重排比」更严；两个结论互相印证。

## 4 这轮没做的事，以及为什么

- **不重建镜像**：#4158 是 draft PR（scope 还在问）、且依赖 #4156。我们的镜像是 `0.2.4p4`（含 rocBLAS 表、
  max-ilp、swizzle、PR #1877），摘两个上游 PR 需要一次完整重建 + 回归，属于独立一轮，不适合塞在相位账里顺手做。
- **不动 `--prefill`**：chunk 尺寸改的是**舍入几何**（上游自己写「The chunk geometry changes the rounding, so it is off by
  default」），按规则 X 必须先过 KL 门 ⇒ 本轮用 10k 档语料跑门（§5）。
- **不试 `prompt-cache-every`**：实测 checkpoint 保存中位 **74.2 ms**、restore 等效 **43,796 tok/s**，
  一次 restore 只要恢复 >48 个 token 就回本。关掉它是纯亏。

## 5 KL 门（chunk 8192 vs 16384）：通过不了「规则 X」，因此**不采纳**

语料：shape 轮 fresh **11,003 / 11,311 token**（chunk 8192 时切成 2 个 chunk、16384 时 1 个 —— 正是要判的变量）；
probe 轮 130-162 token 走窗口打分；**473 个配对位置**，三臂各 485 行。自证：`prompt chunk auto: 8192 /
borrows 1969 slots (4.43 GiB)` 对 `16384 / 3299 slots (7.43 GiB)`。

| 对 | 类型 | KL 均值 | KL 中位 | p90 | p99 | argmax | KL=0 占比 |
|---|---|---|---|---|---|---|---|
| **A∥B**（chunk 8192 -> 16384） | 变更 | **0.060224** | 0.000338 | 0.1926 | 0.8899 | 90.91% | 36.6% |
| A∥C（同一变更，另一份样本） | 变更 | 0.060224 | 0.000338 | 0.1926 | 0.8899 | 90.91% | 36.6% |
| **B∥C**（16384 跑两遍，两次装载） | 底噪 | **0.000000** | 0.000000 | 0 | 0 | **100.00%** | **100%** |

**底噪恰好是 0**（B 与 C 的文件字节数相同、KL 逐位为 0）⇒ 这一段 prefill 在**两个 chunk 都 >= 3072、share 不参与**时是
确定性的。所以 **0.060224 是真信号，不是噪声**。

### 5.1 为什么判「不采纳」

- **规则 X 在这里天然过不了**：变更臂是确定性基线，任何非零差都「大于底噪」。这条规则是为**本身就抖**的开关写的
  （CPU share），对**确定性开关**没有判别力 —— 这是本轮暴露出来的**判据缺口**，不是数据问题。
- 换**绝对口径**看，三个统计量互相矛盾：中位 **0.000338**（比我们采纳过的开关低一个数量级）、
  argmax **90.9%**（与采纳过的 89-94% 同档）、但均值 **0.060**（是 `P103`/`P110`/`P115` 采纳带
  0.003-0.01 的 **6 倍**，也高于 `RT_SKIP` 的 0.0032-0.0058）。
- **上游的态度**：`STRATA_PREFILL_EQUAL`（PR #693）逐字「The chunk geometry changes the rounding, so it is off by
  default」—— 上游把 **chunk 几何当成稳定性边界**，只作 opt-in，不当成可调的性能项。而它自己给的参照是
  「只改 chunk 尺寸 512->1024 = KL 0.052」（#4157/#4159），我们量到的 0.060 与之同量级 —— 也就是说
  **这个改动和上游承认的「纯重排」一样大**，但那不代表它无害到可以随便开。
- **任务级门这次测不了它**：`W805d` 用同一套 36 题跑了两臂（chunk 8192 / 16384），按值都是 **34/36，错的是同两题**
  （t21、t32）。但题目的 prompt 只有 530-568 token —— **两边都是 1 个 chunk，几何根本没变**，
  所以这一车**没有判别力**（顺带再证一次：生产配置在这套题上是 34/36，可重复）。

⇒ **处置：HOLD（不采纳）**，登记 `P131`。要结掉它，缺的是**一个能判确定性改动的口径**，二选一：
(1)跑一套 **prompt >= 8K token** 的任务题（36 题 × 19 s × 2 臂 ≈ 25 分钟）；
(2)给「确定性开关」定一个绝对带（例如「中位 <= 0.001 且 argmax >= 95%」），并在 `W803` 的语料上先把
`P103`/`P110`/`P115` 三个**已采纳**的开关回测一遍，看它们落在这个带的哪里 —— 有了标尺再判 0.060。

## 6 一条被纠正的旧结论：restore 其实在工作

`W800` 当时记「无任何 `restored` 行 ⇒ resume 一律来自热批槽」。**现在不成立**：

```
strata serve: conversation cache: restored 7716 tokens (checkpoint) in 47.6 ms
strata serve: conversation cache: restored 7931 tokens (checkpoint) in 40.0 ms
```

全日志 **283 条 `restored`** / 3,176 条 `parked`。最近 40 次的等效速度：**89,510 tokens / 2,043.8 ms = 43,796 tok/s**
（重读同一段在 640 tok/s 量级 ⇒ 快 **68 倍**）。checkpoint 的保存成本：**中位 74.2 ms**（n=135，59.8-112.7）。

⇒ 会话缓存这条路是**在工作的、而且很划算**；`issue #4081`（只 park 不 restore）在我们这个构建上不成立，
或者至少已经被后续版本修好。这条要写回 `W800` 的结论里。
