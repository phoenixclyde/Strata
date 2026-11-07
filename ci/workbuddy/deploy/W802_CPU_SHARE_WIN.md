# W802 P3 大胜：`STRATA_PREFILL_CPU_SHARE=auto` 在真实多轮 chat 上 **TTFT -23~-29%**

> **【R44 指针 · 2026-11-02 02:2x】生产已按本文结论改成 `auto`。**
> 本文正文里「`share=0`（现役）」指的是 **2026-10-25 的现役**；之后 config 改成
> `STRATA_PREFILL_CPU_SHARE=auto` + `CPU_SHARE_MAX=3072`（`P129` 的 W804 改判）。
> 三者（本文结论 / P129 改判 / 生产值）**一致**，只有 `P23` 的账本正文一直停在「值保持 0」——
> 那是当时为绕开 `gen_config` 缺省问题的临时决定，R44 已更正。

- 日期：2026-10-25 22:26-23:4x
- 触发：`W776 §13` 的 P1（显存安全线）+ P3（CPU share 在 read 200-800 重测）+ P2 侦察
- **本轮最大结论：P23（2026-10 初）对 `STRATA_PREFILL_CPU_SHARE` 的"零收益"否决是区间错配 —— 它在 T=4 测，
  而真实多轮 read=100-350 上这个开关是 -23~-29% TTFT。**
  **但它改答案**（§1.7：两题贪心输出从第 3 个字符起就不同）⇒ 按项目纪律**不进生产**，
  重开为 CANDIDATE，只差一个 teacher-forced KL 门（§1.8 给了做法）。
- 另：`--vram-reserve-mib 768→832` 采纳（零成本消掉 #2065 尾部风险）；`STRATA_MMQ_DIRECT` 在 gfx906 结构性不可用；
  版本核查确认 0.2.5 之后 Qwen 引擎 C++ 无改动。

---

## 1 P3 主结果：CPU share = auto

### 1.1 设计

- bench：`mt_chat.py`（8K 会话、`reused=7,596`、4 轮 read 实测 101/316/125/340、每轮生成 64 token、temperature 0）
- 两臂：`STRATA_PREFILL_CPU_SHARE=0`（现役）vs `auto`；交错 **A B B A A B**，每臂 n=3
- 两臂都开 `STRATA_PREFILL_TIMING=1`（公平），再从日志取每个 chunk 的 GPU timeline
- 每臂断言引擎真实 env 项数（`ENVCHECK`）

### 1.2 结果（带仪器，n=3 中位）

| 轮 | read | TTFT share=0 | TTFT auto | **Δ** | decode 0 | decode auto | Δ |
|---|---|---|---|---|---|---|---|
| T0 | 101 | 1,520.0 [1514-1767] | **1,149.5** [1134-1153] | **-24.4%** | 1,084.7 | 1,491.9 | **+37.5%** |
| T1 | 316 | 2,453.8 [2434-2496] | **1,748.7** [1734-1919] | **-28.7%** | 1,551.3 | 1,447.8 | -6.7% |
| T2 | 125 | 1,676.3 [1558-1846] | **1,319.1** [1254-1323] | **-21.3%** | 942.9 | 999.6 | +6.0% |
| T3 | 340 | 2,500.7 [2404-2689] | **1,953.9** [1883-2285] | **-21.9%** | 955.1 | 972.6 | +1.8% |

**四轮 TTFT 全胜，且四对区间都不重叠**（B 的上界 1153/1919/1323/2285 全部低于 A 的下界 1514/2434/1558/2404）。

### 1.3 相位证据：赢在"小 chunk 的 GPU 时间"

同一个 bench 的 `strata prefill timing`（每个 chunk 的 GPU timeline，ms；只列 read<1024 的 chunk）：

| read | share=0（3 次） | share=auto（3 次） | Δ |
|---|---|---|---|
| 96 | 1,357 / 1,138 / 1,140 | **742 / 747 / 748** | **-45%** |
| 120 | 1,366 / 1,134 / 1,130 | **888 / 781 / 776** | **-32%** |
| 311 | 2,063 / 2,020 / 2,042 | **1,493 / 1,233 / 1,234** | **-29%** |
| 335 | 1,957 / 1,973 / 2,210 | **1,384 / 1,745 / 1,444** | **-26%** |

机理与 `W800` 的相位账完全咬合：CPU share 把「只被少数 token 路由到的专家」从 PCIe 拷贝路径拿走，
`wait copy` + `dequant`（小 chunk 里合计 47%）直接消失一大块；GPU 上剩下的相位占比被动上升
（`hc read` 从 6-8% 升到 12-20%，是分母变小的算术结果）。

### 1.4 无仪器复测（排除"仪器与 share 的测量互相干扰"）

share 的 `auto` 本身要用 CUDA event 量每层 CPU/GPU 时间，而 `STRATA_PREFILL_TIMING` 也插事件 —— 必须分开验。四臂（A B B A，n=2，**不开任何仪器**）：

| 轮 | share=0 | auto | Δ |
|---|---|---|---|
| T0 | 1,607 | 1,184 | **-26.3%** |
| T1 | 2,355 | 1,745 | **-25.9%** |
| T2 | 1,697 | 1,242 | **-26.8%** |
| T3 | 2,366 | 1,828 | **-22.7%** |

- **TTFT 复现**（-23~-27%），且 T0 的 `decode +37.5%` 没有复现（无仪器下 T0 是 -3.9% / +11% 两次，符号不稳）
  ⇒ **那个 +37.5% 是"仪器 × share 测量"的相互作用，不是真实代价**。记下来：**带 PREFILL_TIMING 的 A/B 不能用来判 decode**。
- **KPI-1 不变**：M（21,827 tok）无仪器 `prompt_tps` **699.1 / 689.4 vs 698.5 / 697.4**（中位 694.3 vs 698.0，+0.5%，噪声）
  ⇒ share 只作用于 T<1024 的 chunk，长 prompt 不受影响，符合源码（`cpu_share_on() && !stream_all`）。

### 1.5 为什么 P23 当年判"零收益"

P23 的原文：**"实测（CLI generate，4-token prompt，T<1024 触发，两臂只差该 env）…prefill 928.3 vs 929.5 ms（差 0.13%）"**。
T=4 时 prefill 是**launch-bound**（48 层 × 每层十几个 kernel 的启动开销，约 930 ms 的固定地板，见 `W799`），
专家拷贝只占极小一块 —— **在那个区间里，把专家搬到 CPU 不会改变任何东西**。
到了 T=100-350，拷贝与 dequant 变成 47%，share 的收益就出来了。

⇒ **规则 Q 要加一条（规则 W）**：**"上游没给默认"的第三种原因是"只在别的区间/别的架构验过"**，
而"别的区间"包括**同一张卡上的不同 token 规模**。判一个开关之前，先问"它作用于哪一段相位，那段在我关心的区间里占多少"。

### 1.6 处置

- `P23`：**REJECTED → CANDIDATE（重开）**。理由：否决它的区间（T=4）不适用；新区间收益 -23~-29%；
  但 **parity 不过**（§1.7），按纪律不能直接采纳。
- 生产：**`STRATA_PREFILL_CPU_SHARE` 保持 `0`**（env 仍 11 项）。
  **【W803 已改】** KL 门跑完（六臂、1,348 个配对位置，「开 vs 关」的差 <= 「开 vs 开」的差）⇒ 已改成 `auto` + 钉 `MAX=1024`，env 11→12；冒烟 read 101→1,032 ms、read 316→1,564 ms。见 `W803_CPU_SHARE_KL_GATE.md`。
- 待办（P3b）：`auto` 在极小 chunk 上会跑到 0.9（P23 在 T=4 观到 0.90）；`share` 也可给固定值，
  但**先过 KL 门**——见 §1.8。

### 1.7 parity（采纳门）

两臂各 2 题 × 320 token、`temperature 0`，逐字比对（`w802d_parity_*`）：

| 题 | share=0 | share=auto | 结果 |
|---|---|---|---|
| q0（缓存命中率） | 153 字，`finish=length` | **53 字**，`finish=length` | **不同**（auto 的 320 token 大部分花在思考里） |
| q1（排序四个数） | 96 字，`finish=stop` | 86 字，`finish=stop` | **不同**（结论同为 `4、9、17、23`，表述不同） |

**两题都不同，且答案从第 3 个字符起就分叉**（`S0` 开头是"缓存通常按前缀或固定块匹配"，`SA` 是"缓存容量或上下文窗口固定"）。
⇒ **`STRATA_PREFILL_CPU_SHARE` 在这个 T 上确实改答案**。机理最可能是 CPU 侧专家核（`native_expert` / AVX2-512）
与 GPU 的 MMQ dp4a **求和顺序不同**，贪心解码把这点差别放大。

**P23 当年在 T=4 看到"逐 token 相同"，不能外推**：那是 4 个 token id 的巧合，样本太小。

### 1.8 质量门（下一步，未做）

采纳前必须过两道，做法照本项目既有口径：

1. **teacher-forced KL**（`STRATA_LOGPOS`，两请求法，见 register `P51`）：
   同一 prompt 在 share=0 下取参考 logits，再在 share=auto 下算 KL；**判据：KL 中位 <= 0.01**
   （本项目已采纳的改答案开关都在 0.003-0.01 这一带：`P110` swizzle / `P115-116` GDN / `P103` F16）。
2. **needle 32k 深度 10/50/90%**（第一半已跑，见 §5）。

**若 KL 落在 0.003-0.01 ⇒ 采纳 `auto`（这是本项目至今最大的一笔单点收益：TTFT -23~-29%）。**
**若 KL > 0.01 ⇒ 试更小的固定 share（0.3 / 0.5），看能否把 KL 压回带内、同时保住一半收益。**

---

## 2 P1：`--vram-reserve-mib` 768 → 832（采纳）

现役请求期最低 **506 MiB**，已在引擎阈值（512）下方，每请求打一条
`WARNING: only 506 MiB of VRAM free … (#2065)`。四臂（768 832 832 768，每臂 M×2，无仪器）：

| 臂 | M prompt_tps（2 次） | 中位 | VRAM 告警 |
|---|---|---|---|
| reserve=768 | 690.8 / 692.4 | 691.6 | **2/2 臂出现** |
| reserve=832 | 690.2 / 693.9 | 692.05 | **0/2 臂出现** |

- **代价 ≈ 0**（+0.06%，噪声内）；**收益 = 告警消失**（`#2065` 的后果是 decode 掉到个位数 tok/s，属尾部风险）。
- 成本约 64 MiB 专家缓存（≈28 槽 = 0.28%），无法从 M 上分辨出来。
⇒ 采纳 832（`P62` 的值从 768 更新为 832，证据链接在本行）。

---

## 3 P2 侦察：`STRATA_MMQ_DIRECT` 在 gfx906 结构性不可用（省掉一次 4 分钟 A/B）

`prefill.cpp:1210` 有一条很诱人的路：`STRATA_MMQ_DIRECT=1` 让**驻留专家在缓存槽里被就地读取**
（pointer-table MMQ），省掉 gather 拷贝 + dequant —— 40% 的专家是驻留的，看起来正对症。但：

```cpp
// CMakeLists.txt:1767
if(STRATA_MMQ_TAB AND NOT STRATA_HIP_GFX906)   # gfx906 compiles no .cu from here (its HIP glob): no tab at all
// moe_mmq.cu:494
bool tab_built() { #if defined(STRATA_MMQ_TAB) && !defined(__HIPCC__) return true; #else return false; #endif }
// moe_mmq.cu:559  direct_mode():  if (!tab_built()) { "ignored: this build has no pointer-table MMQ (CUDA with STRATA_MMQ_TAB only)"; return 0; }
```

⇒ **CMake 明确不给 gfx906 编 `STRATA_MMQ_TAB`**，`direct_mode()` 恒 0，`STRATA_MMQ_DIRECT` 在 HIP 上是空开关
（且 `prep_group` 在 `__HIPCC__` 下会直接 `exit(1)`，好在永远走不到）。
按规则 Q 的 (b) 类（"没编进二进制"）**登记为 N/A，不跑实验**。

P2 剩下的唯一整数旋钮是 **`MMQ_GROUP = 16`（`prefill.cpp:1127`，constexpr，experts per MMQ launch）** ——
从未测过，且需要重建镜像。假设：小 M 下每专家一个 launch 的固定开销占比高，把 group 加到 32/64 可以减少
launch 与 gather 次数（代价是 group 缓冲变大、寄存器压力）。**这是 P2 的下一步**，成本 = 一次镜像重建 + 4 臂 A/B。

---

## 4 版本核查：不升 0.2.6

| 区间 | commit 数 | `src/prefill/` | `generate.cpp` | 结论 |
|---|---|---|---|---|
| `v0.2.4.2 → v0.2.5` | 142（187 文件） | **0 文件** | +85 行，只改 `--adapt-async` 默认（CUDA/arena 专用） | Qwen 侧无相关改动 |
| `v0.2.5 → main` | 27（87 文件） | **0 文件** | +2 行 | 其中一条 commit 逐字：**"Version 0.2.6: the Qwen engine packages and Metal stay 0.1.50 (no C++ change since 0.2.5 …)"** |

⇒ 从我们的 0.1.49.2 到 0.1.50/0.2.6，**prefill / 小 chunk / 会话缓存一行没动**
（v0.2.5 release note 里那些 prompt chunk 的改进全是 DeepSeek 引擎自己的 `src/dsv41/`）。
**升级对我们已确认的瓶颈没有收益**，不升。

---

## 5 质量门（第一半）：needle 32k 三深度

| 臂 | depth 10% | 50% | 90% | 合计 |
|---|---|---|---|---|
| share=0 | FOUND 48 s | FOUND 46 s | FOUND 36 s | **3/3** |
| share=auto | FOUND 48 s | FOUND 46 s | FOUND 35 s | **3/3** |

两臂全过、耗时几乎相同 —— 这也是**对照**：32k 的 prompt 是一个 >=1024 的 chunk，share 不作用于它
（源码 `cpu_share_on() && !stream_all`），所以 needle 这条路径本来就不该有收益。
**质量门的真正判据还是 §1.8 的 teacher-forced KL。**

---

## 6 抓到一条工具链陷阱（差点把生产改坏）

改 register 时把 `P23` 从 ADOPTED 改成 CANDIDATE，`gen_config --write` 就不再写 `STRATA_PREFILL_CPU_SHARE`
—— 引擎于是回落到**默认值**，而本机构建的默认恰好是"开"（`P23` 记录过的宏缺陷 `#if !defined(STRATA_USE_HIP)`）
⇒ **生产会静默启用一个改答案的开关**。

发现方式：推完立刻查 `env_n`（11 → 10、`share=None`），随即回滚。**纪律**：
(1)一个参数一旦"被显式设过"，就必须永远保留一条 ADOPTED 行（值可改、状态不能摘）；
(2)每次推配置后必须同时核 **config 的 env_n** 与 **引擎进程的 `/proc/<pid>/environ` 项数**（本次两处都查了）；
(3)`CANDIDATE` 只用于"从未进过生产"的参数，不能用来表达"已采纳但想重估"。

---

## 7 状态与下一步

生产：`0.2.4p4` / **env 11 项**（`PREFILL_CPU_SHARE` 仍 0；`--vram-reserve-mib` 768→832；**W803 之后为 env 12 项、share=auto**）/ 
`verify_config` **PASS=35 FAIL=0** / `gen_config --live` 无差异 / 引擎进程 env 计数 11。
回滚位：`strata-huihui-ud-iq4_xs.json.bak_w802_832`。

下一步（按收益）：
1. **P3b**：share 固定值扫描（0.5 / 0.65 / 0.8 vs auto），判 TTFT 与 decode 的折中（需要先过 parity）。
2. **P2**：`MMQ_GROUP` 32/64（重建镜像）—— 小 chunk 的 `gemm gate/up` 与 decode 的 `VRAM hits` 都在这里。
3. 把 chat bench 固化成回归闸（每次改动跑一遍 4 轮，TTFT 与 decode 分别判）。
