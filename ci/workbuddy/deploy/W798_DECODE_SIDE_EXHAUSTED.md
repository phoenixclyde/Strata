# W798 decode 侧：7 个开关单轮全否，但真正的产出是「decode 端到端不可判」

- 日期：2026-10-25 19:47-20:45
- 触发：`W776 §12.10` 队列第 1 项（decode 侧 10 个开关）
- 结果：**没有采纳任何参数**；产出两条方法学（规则 K 的答案 + 规则 R）与一条结构性判据（`arch_default_env` 空表为何合理）

> **【AUDIT9 更正 2026-10-25 22:5x】四条（结论全部不变）：**
> 1. **§3.1「单调下降 27%」不成立**：序列 4,579→3,815→3,858→4,062→3,483→3,198 **非单调**（两处上升）；
>    27% 是脚本的"极差"，r1→r6 实为 **-30.2%**。
> 2. **§2「262 tokens 花了 1,953 ms ⇒ 0.104 ms/token」分母错**：1,953/262 = **7.45 ms/token**；
>    0.104 = 1,953/**18,876**（复用 token 数）。
> 3. **§4 相位表标注"取 r2-r4 中位"，实际切片是第 3-5 行**（`rows[2:5]`；首行是 2-window 冷启）。
>    按字面 r2-r4 重算：C 的 `waitCPU` **+46.4%**（非 +25.0%）、D 的 `VRAM hits` **+36.2%**（非 +37.7%）、
>    C 的 `PCIe grp` +8.7%（非 +1.5%）。**方向与量级不翻**，但口径必须写死成"第 k 行"。
> 4. **§1 的 `SH_STREAM +10.8%` 用的是本文自己判死的通道**：A 臂 `MEDIAN decode_ms` 内部极差 **27.0%**，
>    且同配置连跑两次是 5,375.6 / 5,283.4（比 A 臂高 51%）。
>    ⇒ 应写"端到端观测到同向变慢，**幅度不可判**"；否决依据改用源码逐字（R9700 fork off 62.9 vs on 43.4 t/s）。

---

## 1 结论先行

| 开关 | 结果 | 硬证据 |
|---|---|---|
| `STRATA_SH_STREAM=1` | **否决**（依据＝源码，不是端到端） | 端到端观测**同向**变慢（幅度不可判：该通道自身极差 27%，见 §3.3）；源码注释逐字已预示（HIP 跨流 event 依赖比共享专家本身还贵：R9700 上 62.9 → **43.4 t/s**） |
| `STRATA_Q8_PACKED=1` | **否决** | 靶相位 `q8+qkv/q-idx gemv` **+8.1%**（确实生效）、`waitB` +21.6%、`waitCPU` +25.0%；**吃 +1912.5 MiB、专家槽 9901 → 9046（-855）** |
| `STRATA_EXPERT_V2=1` | **否决** | `VRAM hits` **+37.7%**、`Q:VRAM hits` **+38.6%**，同时 `waitCPU` **-39.3%** |
| `STRATA_LFUSE=1` | **无效** | 相位全平（-2.7 ~ +1.7%），端到端 +0.3% |
| `STRATA_GDN_SPLIT=1` | **否决** | `rec` 相位 **+37.8%**，其余全平（+0.2~2.8%），端到端 r3/r4 慢 6.7%/9.7% |
| `STRATA_TSUM=1` | **无效** | 相位全平（-1.4 ~ +0.3%） |
| `STRATA_QFUSE=1` | **未判（需复测）** | 端到端出现 **488 / 2012 ms** 的不可能值（256 tokens 至少 3 s）；相位全面 -10~-25% 但 `waitB` **+20.7%** ⇒ 数据自相矛盾 |

**最有用的一句**：`arch_default_env` 只给 gfx12 / gfx1151，不是遗漏 —— 本轮 7 个里有 **4 个在 gfx906 上确实生效，方向全部反了**。它们的收益来源（统一内存、更宽的 LDS/带宽、wave32）在这张卡上不存在。

---

## 2 规则 K 的答案：多轮场景 decode 占 64-83%

单轮口径下 decode 只占 M 档 15%、L 档 0.5%，所以过去七轮都没动它。但**多轮对话里 prompt 大部分复用**：

| 轮次 | prompt_tok | reused | prompt_ms | decode_ms | 端到端 | **decode 占比** |
|---|---|---|---|---|---|---|
| 1（冷） | 18,876 | 0 | 27,189 | 4,964 | 32.2 s | 15% |
| 2 | 18,901 | **18,871（99.8%）** | 787 | 3,878 | **4.68 s** | **83%** |
| 3 | 19,114 | 18,896 | 1,578 | 3,586 | 5.18 s | 69% |
| 6 | 19,910 | 19,648 | 1,953 | 3,499 | 5.47 s | **64%** |

顺带两个必须分开的数：第 6 轮 `prompt_read` 只有 **262** tokens，却花了 **1,953 ms**——那是 1,953/262 = **7.45 ms/read-token**；换算到**被重放的 18,876 个复用 token** 上是 1,953/18,876 = **0.104 ms/复用-token**。两者不是同一个量。

---

## 3 端到端 decode 不可判：三条独立证据

这一节是本轮最重要的方法学产出，因为它推翻了"用 duration/decode_ms 做 decode A/B"这个做法。

### 3.1 v1 基准（6 轮都问"数数字"）：27% 的假趋势

| 轮次 | r1 | r2 | r3 | r4 | r5 | r6 |
|---|---|---|---|---|---|---|
| decode_ms | 4,579 | 3,815 | 3,858 | 4,062 | 3,483 | **3,198** |

**波动下行**（r1→r6 **-30.2%**，但 r2→r3、r3→r4 各有一处回升，**不是单调**；27% 是脚本给的 arm 内极差）。原因不是热漂移（同一次运行的 idle 温度 46 °C、负载后 53/61 °C），而是**内容的自我强化**：
每轮都要求"从 1 数到 200"，历史里全是可以被 draft 直接命中的数字序列 ⇒ **轮次越后，draft 接受率越高** ⇒ 看起来"越来越快"。

### 3.2 v2 基准（6 轮问题各异）：轮间根本不可比

| 问题 | decode_ms |
|---|---|
| 数 1-200 | **4,377** |
| 解释什么是内存带宽 | **5,465** |
| 写一段秋景 | 4,953 |

同一台机器、同一 env，**不同问题之间差 25%** ⇒ "平均值"没有意义。

### 3.3 两次测量方向相反

`STRATA_Q8_PACKED=1` 在 W798（v1 基准）里 r4/r5/r6 都更慢（+6.7 / +22.7 / +38.9%），
在 W798d（相位基准）里端到端反而**快 2.8%**（3,662 vs 3,766）。而相位说它 `waitB` +21.6%、`waitCPU` +25.0%（更慢）。

**⇒ 端到端 decode 的单位置噪声 7-35%，大于要测的效应量级。不能再用了。**

---

## 4 规则 R（立）：decode 侧 A/B 必须用 `decode GPU stages` 分相位

`STRATA_VERIFY_PROFILE=1` 打印的 `strata decode GPU stages (ms/window)` 是**GPU 事件计时**，分项直接对应各开关的作用点：

```
GDN layers: q8+qkv/q-idx gemv | conv | ab | z | rec | out-proj | router+plan+bell | shared+quant |
            waitA | VRAM hits | waitB | PCIe grp | waitCPU | copy+combine | (gap) | head | hc0/hc1 norm/down/up
QSA layers: q8+kv-idx | k/v+norm-rope | kv+idx append | q+q-idx | scores+topk | kv-resolve | attention |
            gate | out-proj | router+plan+bell | shared+quant | waitA | VRAM hits | ...
```

本轮实测的相位账（A 为基线，**取每个 6 行转录里的第 3-5 行**；首行是 `over 2 windows` 的冷启，故不是字面的 r2-r4——按字面重算 `waitCPU` 会变成 +46.4%、`VRAM hits` +36.2%，方向不变）：

| 相位 | C `Q8_PACKED` | D `EXPERT_V2` | E `LFUSE` | B `GDN_SPLIT`（第二批） | C `TSUM` |
|---|---|---|---|---|---|
| `q8+qkv/q-idx gemv` | **+8.1** | +0.7 | +0.4 | +0.4 | +0.0 |
| `rec` | +1.4 | -1.4 | -2.7 | **+37.8** | -1.4 |
| `out-proj` | +0.5 | 0.0 | 0.0 | 0.0 | 0.0 |
| `shared+quant` | +1.1 | +4.0 | -0.6 | +0.6 | -0.6 |
| **`VRAM hits`** | -1.0 | **+37.7** | +0.1 | +0.2 | +0.3 |
| `waitB` | **+21.6** | -1.1 | 0.0 | +1.1 | 0.0 |
| **`waitCPU`** | **+25.0** | **-39.3** | -7.1 | -8.5 | -6.8 |
| `PCIe grp` | +1.5 | **+20.0** | -1.5 | 0.0 | -1.5 |
| **`Q:VRAM hits`** | -1.3 | **+38.6** | 0.0 | 0.0 | -6.8 |

**`waitCPU` 与 `VRAM hits` 是一对**：两者之和接近常数 ⇒ 它们互相转化。
`EXPERT_V2` 把 `waitCPU` 的 39% 转成了 `VRAM hits` 的 +38%（专家计算从"与别的东西重叠"变成"串行进主路径"）—— 这正是它在 gfx1151（统一内存、带宽充裕）上省钱、在 gfx906 上亏钱的原因。

### 4.1 两个必须记住的陷阱

1. **`STRATA_DECODE_TIMING` != `decode GPU stages`**。前者是墙钟行（含 adapt wait / join），后者属于 `STRATA_VERIFY_PROFILE`。
   本轮先用错了 env，跑完一轮才发现 `grep -c "decode GPU stages"` = **0**。
2. **profiler 会关掉 `SH_STREAM` 的 fork**（源码逐字「The profiler turns the fork off to time the stages」）
   ⇒ 带 profiler 根本测不了它，只能靠端到端 + 源码注释。

---

## 5 逐项细节

### 5.1 `Q8_PACKED`：生效了，但用 1.9 GB 显存换 8% 的相位退化

引擎逐字打印 `native dense: STRATA_Q8_PACKED=1 packed 84 Q8_0 matrices for decode (+1912.5 MiB)`。
**专家槽 9901 → 9046（-8.6%）**，而当前 `vram_free` 只有 606 MiB。

相位上它确实动了该动的地方（`q8+qkv/q-idx gemv` +8.1%），但方向是变慢，且 `waitB`/`waitCPU` 一起涨。
⇒ 在"显存只剩 606 MiB、专家槽是要用来兜 prefill 的"这个前提下，**没有任何采纳理由**。

### 5.2 `GDN_SPLIT`：与 W797 的 GDN 结论方向相反，原因是 T

- **prefill**（W797，`STRATA_GDN_HEAD=1` + `GDN_PP=2`）：`gdn recurrence` **-50.2%(M) / -45.6%(L)** —— 大胜
- **decode**（本轮，`STRATA_GDN_SPLIT=1`）：`rec` **+37.8%** —— 大败

同为 GDN recurrence，机制不同：prefill 是 **4 lane/列、批量 token**（HT=4 tokens 一级流水，LDS 复用摊得开）；
decode 是 **4 块/head、T=1**（每块只算 32 列，同步与 launch 摊不开）。
⇒ **同一个算子，prefill 的分块策略搬到 decode 上是负的**（也解释了为什么上游给它们不同的开关）。

### 5.3 `SH_STREAM`：源码注释已经把结论写死了

> On HIP a cross-stream event dependency costs more than the shared expert takes to run, so there the fork **starts off**:
> R9700 (gfx1201) the fork off decodes at **62.9 t/s against 43.4 t/s** with it on.
> **Strix Halo (gfx1151, unified memory) is the exception** … so the gfx1151 arch table sets `STRATA_SH_STREAM=1`.

我们实测慢 **10.8%**，与之一致。默认 `#if defined(STRATA_USE_HIP) return false` 是对的。

---

## 6 结构性判据：为什么 `arch_default_env` 空表是合理的

把 W797（GDN 组，**胜**）与 W798（decode 组，**全败**）对照，规则就清楚了：

| 类别 | 例子 | 收益来源 | gfx906 上 |
|---|---|---|---|
| **纯内核结构改进** | `GDN_HEAD`/`GDN_PP`（4 lane/列、两列/lane） | 循环次序、LDS 复用、归约方式 | **有效（-50%）** |
| **依赖内存/带宽模型** | `SH_STREAM`（跨流重叠）、`EXPERT_V2`（把等待换成计算） | 统一内存、带宽充裕 | **反向（+10.8% / +37.7%）** |
| **拿显存换速度** | `Q8_PACKED`（+1912 MiB） | 多一份 packed 拷贝 | 我们只有 606 MiB 余量 ⇒ 不可行 |
| **架构特化** | `PF_GEMM`/`PF_PAD`/`PF_HCDOWN`（`#else return false`） | gfx11 矩阵核 | **没编进二进制** |

⇒ 以后看到 `arch_default_env` 里 gfx1151 的项，**先按这条分类，再决定要不要测**。
规则 Q 的(c)（真的更差）在这一类上是常态，不是例外。

---

## 7 残余风险与未做

1. **`QFUSE` 未判**：端到端出现 488 / 2012 ms（256 tokens 不可能），相位全面 -10~-25% 而 `waitB` +20.7%。
   数据自相矛盾，只能复测。**未采纳**。
2. **`Q6_PACKED` / `MMVF_ROWS` / `PLE_BATCH` 未测**（三个）。按 §6 的分类，前两个属"拿显存换速度"（`Q6_PACKED` 是另一份拷贝），
   `PLE_BATCH` 属"减 launch"，优先级低。
3. **decode 相位的噪声没系统量化**：本轮每臂只有 3 个样本（r2-r4），用的是"变化 >5% 才算"这个粗门槛。
   A 臂自身的相位极差没有单独测（`rec` 在 A 的三轮里应该稳，但没量）。
4. **生产曾被污染一次**：`W798e` 的恢复逻辑 drop 列表漏了 `STRATA_DECODE_TIMING`（它是 `W798c` 加的），
   导致生产 env 一度多一项。已清理并复核（`STRATA_DECODE_TIMING` = ABSENT，slots 9901 / vram 606）。
   ⇒ **教训：恢复脚本的 drop 列表必须"按历史全量"写，不能只写本脚本自己加的。**

---

## 8 生产状态（未变）

`strata166-407` / `strata-gfx906:0.2.4p4` / 0.1.49.2 / slots **9901** / vram_free 606 / governor schedutil /
**env 10 项**（`HSA_OVERRIDE_GFX_VERSION`, `PREFILL_CPU_SHARE=0`, `RESIDENT_HEADROOM_GIB=0.5`, `HC_Q8=1`,
`HIP_PROMPT_F16=1`, `ROCBLAS_TUNING=…`, `GFX906_ATTN_QUERY_SWIZZLE=1`, `SELECT_SIMT=1`, `GDN_HEAD=1`, `GDN_PP=2`）。
