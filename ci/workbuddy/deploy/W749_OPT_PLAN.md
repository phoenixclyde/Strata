# W749 优化方向、方案与计划（含 routeK 库的源码级思路）

> **W751 状态**：本件的全部实质内容（方向分层 / routeK 源码级思路 / 死路清单 / 三条测量纪律 /
> 源码级引证表）**已并入 `W750_MASTER_PLAN.md`**；W750 之后又被 **`W832_OPT_PLAN_V2.md`（当前唯一权威）** 取代。
> 本件保留为**引证层**，供逐条溯源用（W750 §7.5 的引证表即从这里的 §5 并入）。
> 指针腐坏（原横幅只指到 W750）已在 **AUDIT23 P1-2** 修正。

日期 2026-10-10 01:5x ｜ 引擎 0.1.41 ｜ 卡 MI50 32GB (gfx906) ｜ pack huihui-UD-IQ4_XS

## 0 一句话现状

单流 + 现 pack + 现引擎，**参数面已收敛**（W747 自比证明现役配置就是我们跑过里最快的），
`EXPERT_V2`/`TSUM` 已否决；**但四类空间都还开着**：上游 §4 开关族（只测了 12 个里的 2 个）、
`--mtp-window` 的默认未被审视、非专家张量的精度面、以及**并发吞吐的空白**。

## 1 本波实读的三个证据源（不是转述）

1. **Strata 源码（本机 `deploy/tmp/src411/Strata-0.1.41`）** ---- 逐行核到 `--mtp-window` 默认与草案策略。
2. **routeK 的自有库**（`phoenixclyde/vllm-gfx906-mobydick` @ `gfx906-patches-030`，7401 文件）----
   本波实读 5 件并落盘：`DEAD-ENDS.md`(26,725 B)、`DEVLOG-moe-residency.md`(2,635)、
   `DEVLOG-mtp-depth-matrix.md`(6,217)、`DEVLOG-spec-decode.md`(41,131)、`PROFILE-k4-step-ledger.md`(15,414)。
   （按铁律：**引用 routeK 结论一律读它的树**，归档件 `ARCHIVE.md` 只作对照。**体量口径**：下文与该件其它处引的 routeK 原文体量均为 **chars**，对应 UTF-8 **bytes** 各为 27,118 / 2,670 / 6,318 / 41,758 / 15,614 ---- W752 审计 #6 指出未标单位。）
3. **生产实测**（W747 自比 / W748 复现 59.9）。

## 2 方向分层

### A 档 ---- 上游已给数据、我们未做（low risk，先做）

| 序 | 项 | 现状 | 上游数据 | 零风险？ |
|---|---|---|---|---|
| **A1** | **`--mtp-window`**（register **P43**） | **默认 32768，我们没设** | `docs/STRIX_HALO.md:126-127`：**64K output +3.5%、32K -0.4%**，且明说"**not Strix-specific**" | **是**（只改验证窗口） |
| A2 | `STRATA_SH_STREAM`（**P40**） | 未设 | UD-IQ4_XS decode **+1.8%**；byte-identical | 是 |
| A3 | §4 其余开关（**P41**） | 12 个里只测 2 个 | 全族 output +3.9~5.0%（gfx1151） | 是（声明 byte-identical） |
| A4 | `--lookup-chain`（**P42**） | 未登记 | 上游生产配置用它（=3），未给单独增益 | 是（只选草稿，不改输出） |

**A1 是当前最实的一条**：默认值就摆在那里未被审视，而本机确有 82k/92k 长会话（W743：解码仅 36-38 tok/s）。
源码依据：`src/program/generate.cpp:552` `int64_t mtp_window = 32768;` / `:1801` 是它的 CLI。

### B 档 ---- 从 routeK 库挖到的源码级思路（本波新增）

**B1 `DraftPolicy` 的窗口成本曲线是借来的（RTX 5070 的）**  ← 本波最独特的一条

- Strata 的草稿深度是**在线自适应**的（`src/spec/draft_policy.cpp`）：每轮在 MTP 窗口与 suffix lookup 窗口之间，
  按 **期望提交 token / 实测 round ms** 取大者；`kCostAlpha=0.1` / `kTokAlpha=0.05` 是它的 EMA。
- **但"未测过的窗口尺寸"靠一条先验形状外推**，而那条形状的注释逐字写着：
  *"Between the **RTX 5070's** measured curves: +10 ms per token with every missed expert on the CPU"*
  （`draft_policy.cpp:9-12`，`kShape[] = {0, 1.0, 1.35, 1.7, 2.05, 2.45, 2.85, 3.25, 3.6}`）。
- **含义**：gfx906 上若"窗口变大"的代价曲线形状不同（PCIe 搬运会让它更陡），
  冷启动阶段策略会**按 CUDA 的形状选深度**。长期会被 EMA 校正，但前若干轮会偏。
- **做法**：固定负载、扫 `--mtp-max-t`/窗口各档，实测 `ms/step` 与 `net/step`，与 `kShape` 比形状。
- **判据**：实测曲线与 `kShape` 的相对偏差；若超过噪声（我们既有分辨力：解码 9.5~15%），
  则值得**给 gfx906 标定一条曲线**（源码注释里那套"measured curves"就该有第二条）。
- **注意**：这是**策略标定**问题，不是正确性问题 ---- hpp 头部逐字 *"It only chooses which drafts to verify: **the output is unchanged**"*。

**B2 非专家张量的 int8（W8A16）面**（routeK 的 T1，PROBE GO）

- routeK 在**同一张卡**上实测：把**未量化的 BF16 质量**（lm_head / FA qkv / GDN proj / shared expert / MTP draft 层）
  做 int8，**lm_head 1.93x、其他 floor-bound 形状 2.00~2.42x**；**per-channel scale 比 per-128-group 好 28%**；
  天花板 **dense +10~13% / MoE +14~19%**。同页还写明 *"this does not contradict the D row ('lm_head GEMV lever does not exist'):
  that killed **kernel-side** wins at the floor; this is the **byte-side** lever"*。
- **前提核查（未做）**：Strata 的非专家张量当前是什么精度（我们的 pack 只查到 expert 是 `IQ3_S/IQ4_NL`）。
  -> **第一步是只读核查，不是改代码**。
- 依据：routeK `DEAD-ENDS.md` 的 OPEN 表（T1 行）+ `int8-investigation-qwen.md`。

**B3 逐桶账（per-bucket ledger）** ---- 定位我们的长上下文代价

- routeK 的方法（`PROFILE-k4-step-ledger.md`）：CUDA-event 包住代表性模块，把一步拆成
  `full_attn / lin_attn(GDN) / mlp / drafter / 各 head`，**桶的覆盖约 100%**，step-bracket 与端到端差 **~2%**。
  结论：**full_attn 是唯一随上下文增长的桶**（64k->120k 增长里占 **87%**；64k 已占 45%，120k 占 57.5%）。
- 我们目前只有 stage 级 timing（`--stage-timing`）-> 做不了这种归因。而 W743 已证**长上下文解码只有 36-38 tok/s**（短上下文 43-60）。
- **做法**：先看 Strata 是否已有更细的 profile 钩子；没有则用 `--stage-timing` 的现有粒度 + 分段请求反推。
- **判据**：能否把"长上下文那 30% 的差"归到单一桶上。

**B4 三条测量纪律（routeK 用血换的）**

routeK `DEAD-ENDS.md` 的 *"The recurring lessons"* 逐条：
1. **standalone harness 的胜不迁移到 serving wall-clock**（profiler/launch 状态依赖，eager 也一样）；
2. **serving 的 graph A/B 才是 µs 级判决的门**，eager A/B 可能在核不同时仍打平；
3. **PPL/prompt_logprobs 在混合注意力模型上不可靠**（Gemma-4 案例），要用**连贯文本 + logprob** 双门。
=> 我们已有的纪律（`MEMORY.md`：判「改答案」按 index 跨臂对齐、探针须落盘）与这三条同源，可直接并表。

**B5 同芯片的可引用常量（routeK 实测，省我们一轮）**

- **L2/TCC = 8 MB**（两块 MI50 都是），**HBM 流式下限 804~809 GB/s**（W=256 MB 冷读）；
- 小工作集读是**延迟受限**而非容量受限（子 L2 带宽反低于 HBM 下限）；
- **生产 gemm1 M=1 内核实测只到 194~196 GB/s = HBM 下限的 24%**（该工作集可达读带宽的 58~64%）
  => **M=1 的绑定约束是延迟/占用（MLP），不是 HBM 地板，有 2 倍以上余量**。
- 出处：`DEVLOG-moe-residency.md`（本波落盘 `deploy/tmp/_w749_DEVLOG-moe-residency.md`）。

### C 档 ---- 结构性 / 空白

| 序 | 项 | 状态 |
|---|---|---|
| C1 | **专家驻留 / 命中率**（我们实测证实它主导：W748 hit 0.774 -> 0.963 使单步 92 -> 53 ms） | 容量面议题，未动 |
| C2 | **并发吞吐**（`--batch/--slots` 从未测） | **完全空白**：单流已调到位，但"能同时服务几个"没有任何数据 |
| C3 | `--kv` 四档的**质量门（KLD）** | 未做（长上下文才吃） |

## 3 routeK 已证死的路（**我们不要重复**）

| 死路 | routeK 的判决与量级 |
|---|---|
| 换更强的 dot 指令救 decode | **FULLY DEAD**：`v_dot4_i32_i8` 已是内环且实测满速（4.44x fp32）；B=1 decode 是 **gather-HBM-bound ~2.7x**，ALU 换不动；解包复合只有 0.17~0.24x。**与我们 W740 的判决一致** |
| A8W8（int8 激活 x int8 权重）GEMM | **DEAD-END**（Triton 实测 0.59~0.68x hipBLAS fp16；手写版**范围算术**先判死：BF16 质量只占 7.9/8.9% 的 MAC，完美 1.96x 内核只赢 ~3% wall） |
| MTP 深度 k=4 / k=5 | **k=4 LOSS**（合成负载的胜不迁移）；**k=5 只有"完美接受的天花板"**，从未在真实负载验证 |
| `--disable-custom-all-reduce` | **NEUTRAL（no-op）**：后端自己会 self-disable |
| vLLM custom all-reduce（P2P） | **NO-GO**：**输出乱码**（1/96 token 与基线一致）---- 附带一条方法教训：`stop_agreement`/`rep_frac8` **抓不到坏分布**，必须有文本/logprob 门 |
| KVSPLIT=32 全形状统一 | **REJECTED（bit-exact -10%）**，改成 shape-aware（Sq>=4 用 32、Sq=2 用 16） |
| SYV-12 context-lookup verify / FA V2 fused gather / C1 stage2 fused topk | 分别 **DEAD-END / REJECTED / DEAD-END**（后者是"孤立->服务 翻转"的第 3 次） |
| QSA full CUDA graph / GGUF plugin（qwen4exp） | **DEAD-END / NO-GO**（HIP 拒绝 capture；无 GGUF->HF 映射） |

## 4 计划（按"证据强度 x 成本"排）

| 序 | 项 | 做法 | 成本 | 验收判据 | 预期 |
|---|---|---|---|---|---|
| **1** | **A1 `--mtp-window`** | 单变量 A/B：默认 32768 vs 8192（长上下文 >=64K，Z0=off，交错 >=3 对） | 低（改 config + 重启 + 一组长请求） | 同形状、带 hit 与 reused 的 ms/step | 上游 64K **+3.5%**；32K **-0.4%**（意味着要**分上下文**给值） |
| **2** | **B2 前提核查**（只读） | 核 Strata 的 lm_head / attn qkv-o / GDN proj / shared expert / MTP draft 层当前精度 | **极低**（只读 pack 清单 + 源码） | 能列出各张量的类型与字节占比 | 若大量是 fp16/bf16 => 引出 byte-side lever |
| 3 | **B3 逐桶账** | 看 Strata 有无更细钩子；无则用现有粒度 + 分段反推 | 中 | 长上下文那 30% 差能否归到单桶 | 定位"长上下文慢"的真实桶 |
| 4 | **A2 `SH_STREAM`** | 单变量（byte-identical） | 低 | 同形状 ms/step | 上游 +1.8% |
| 5 | **C3 `--kv` 质量门** | 四档 KLD 主门 + PPL/c1/c16 同车（**禁 PPL 单独做门**） | 中 | KLD 门通过 | 只影响长上下文 |
| 6 | **A3 §4 其余** | 逐个单变量（**必须串行**，W723） | 中（10+ 个） | 同形状 | 全族 +3.9~5.0%（gfx1151 的数，**不可照搬**） |
| 7 | **A4 `--lookup-chain`** | 单变量 | 低 | 同形状 | 未给单独数，期望低 |
| 8 | **B1 `kShape` 标定** | 扫窗口档测 `ms/step` vs `kShape` 形状 | 中 | 形状偏差是否超 9.5~15% 分辨力 | 若超 => 值得给 gfx906 一条曲线 |
| 9 | **C2 并发面** | 先只测"两路并发时的单路退化"，再谈 batch/slots | 中高 | 吞吐 vs 单路时延的曲线 | **无先验**，纯探索 |
| 10 | **B5 常量入账** | 把 L2=8MB / HBM 下限 ~805 GB/s 记进 register 作参照 | 极低 | 账本可查 | 省未来一轮 |

**排序理由**：1 是"默认值未被审视 + 上游有数"；2 是**纯只读**且能证伪/证实一整条路线；
3 是**方法**（决定后面所有长上下文工作的靶心）；其余按风险递增。

## 5 源码级引证（可逐字复核）

| 断言 | 位置 |
|---|---|
| `mtp_window` 默认 32768 | `src/program/generate.cpp:552` `int64_t mtp_window = 32768;` |
| `--mtp-window` / `--mtp-max-t` 是 CLI | `generate.cpp:1801` / `:1839` |
| `mtp_max_t` 默认取 `--spec` | `generate.cpp:2198` `if (o.mtp_max_t == 0) o.mtp_max_t = o.spec;` |
| `spec` 上限 8（kVerifyMaxT） | `generate.cpp:2199` |
| 窗口上限 8 | `include/strata/spec/draft_policy.hpp` `static constexpr int kMaxT = 8;` |
| 成本曲线来自 RTX 5070 | `src/spec/draft_policy.cpp:9-12`（注释 + `kShape[]`） |
| 策略只选草稿、不改输出 | `include/strata/spec/draft_policy.hpp` 头部末句 |
| suffix drafter 朴素用法会输 2-8% | 同上（"Taken whenever it proposes more than the MTP, it lost 2-8% on ordinary text"） |
| routeK L2=8MB / HBM 下限 805 GB/s / 内核只到 24% | `docs/gfx906/DEVLOG-moe-residency.md`（本波落盘） |
| routeK k=3 甜点由 FA tile 决定 | `docs/gfx906/DEVLOG-mtp-depth-matrix.md`（`Sq_pad=4` vs `Sq_pad=8`） |
| routeK 死路清单 | `docs/gfx906/DEAD-ENDS.md` |
| routeK 逐桶账方法 | `docs/gfx906/PROFILE-k4-step-ledger.md` |

## 6 纪律与局限

- **口径**：任何"快了/慢了"的结论必须同时带 **gen / 草稿接受 / hit rate**（W744/W748 已两次踩）。
- **不可跨生成长度或冷温比 tok/s**；不可用 4~6 点线性外推（会出现假负斜率）。
- **routeK 是 vLLM、我们是 Strata**：可移植的是**芯片级事实与机制判据**，**不是内核代码**
  （routeK 树里 `fused_gr` / `s2_expert_grouped` / `native_mmvq` / `iq_kernels` 计数为 0，W737 已证）。
- **上游 §4/§5 的数字是在 gfx1151（统一内存）上取的**，我们已测的两个同族成员在本卡是负的 => **不可整族照搬**。
- 本报告只列方向与判据，**不含任何未实测的收益承诺**。

## 7 证据件

| 件 | 内容 |
|---|---|
| `deploy/tmp/_w749_DEAD-ENDS.md` | routeK 死路清单原文（26,725 B） |
| `deploy/tmp/_w749_DEVLOG-moe-residency.md` | L2/HBM/内核带宽实测（2,635 B） |
| `deploy/tmp/_w749_DEVLOG-mtp-depth-matrix.md` | MTP 深度矩阵（6,217 B） |
| `deploy/tmp/_w749_DEVLOG-spec-decode.md` | 投机解码全日志（41,131 B） |
| `deploy/tmp/_w749_PROFILE-k4-step-ledger.md` | 逐桶账（15,414 B） |
| `deploy/tmp/src411/Strata-0.1.41/src/spec/{draft_policy.cpp,draft_policy.hpp}` | Strata 侧（已在本机树内） |

**例外**：`deploy/tmp/_w749_*.md` 五件是从**自有库逐字取回**的 routeK 原文，含作者自带的
箭头/破折号/省略号/不等号等码位（U+2192、U+2014、U+2013、U+2026、U+2265、U+2264、U+2212、U+00D7；各件 CR=0），
**按第三方原文先例不重写**（同 W734 对上游 `app.js`、W740 对自有库技能原文的处理）。本报告与账本自身 BAN=0。
