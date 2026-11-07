#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: the root cause into the plan and the report, plus the P463 retraction."""
import io

# ---------------- plan ----------------
P = "deploy/W832_OPT_PLAN_V2.md"
s = io.open(P, encoding="utf-8").read()
add = """
**十三、根因找到了：这七组 KL 是同一个数，度量测的是模型的混沌放大（`P468` / `P469` / `P470` / `P471`）。**

四臂（外加基线）的**七组两两** KL，全部落在 [0.0354, 0.0465]，跨度只有 1.31×：

| 对比 | 两者的扰动差 | KL |
|---|---|---|
| ctl vs `CTLREAD` | **1e-7** | 0.04111 |
| ctl vs `F16Q` | 1e-5 | 0.04479 |
| ctl vs `F16D` | 1e-5 | 0.03798 |
| ctl vs `DP4A` | **1e-2** | 0.04130 |
| **`CTLREAD` vs `F16Q`** | 1e-7 vs 1e-5 | **0.04221** |
| **`DP4A` vs `F16D`** | 1e-2 vs 1e-5 | **0.03544** |
| `CTLREAD` vs `DP4A` | 1e-7 vs 1e-2 | 0.04650 |

**决定性的一行是 `CTLREAD` vs `F16Q` = 0.04221**：两者都只差 1e-7~1e-5，若这个度量反映精度，它们彼此应该 ≈0；
实测与「差 1e-2 的 DP4A vs 基线」**一样大**。⇒ 任意两臂之间的距离都等于同一个常数 —— 这是**混沌映射**的统计距离。

**机制**：1e-7 的扰动经 48 层残差放大到 O(1e-2)，在 softmax 上把近 ties 翻边；于是**任何非零扰动都落到同一个宏观距离**上。
而 `REDUCE12` / `DPP` 两臂是**逐位不变**（零扰动），所以地板恰好是 0.00000。

**外部证据（上网核实）**：Yuan 等 2025《Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference》实测
仅改 batch / GPU 就让准确率波动最多 **9%**、响应长度差 **9,000 token**，根因就是浮点非结合性；
Thinking Machines《Defeating Nondeterminism in LLM Inference》把批次相关内核行为列为主因；
多方一致的结论是「**80 层模型每层几个 ULP，足以翻转相当比例 prompt 的 argmax**」。

**⇒ 旧数值门（对逐位相同基线求 KL ≤ 0.0139 / top-1 ≥ 99%）对任何算术改动都不可能通过。**
`P453`/`P456` 的 FAIL 是这道门的性质，不是 DP4A / F16D 的质量。

**新的判据（`P470`，已立）**：① 地板臂必须 0.00000；② **同噪控制臂**（可证等价的算术重排，本轮 `CTLREAD` 实测 **0.0411**）
给出噪声地板；③ 候选 **≤ 地板 ⇒ 不可判**，**≥ 2× 地板才算有害**。按此，DP4A/F16D/F16Q 三者**全部落在地板带内、彼此不可区分**。

**同时撤回一条（`P469`）**：`P463` 的「`<..,16>` 被展平成 7087 条 / 408 个载入点」是**错的**——那个 fatbin 是在 pa7 重编**之前**
（12:23 vs .o 12:24）dump 的，里面还是 pa8 的 `printf` 版（`global_atomic_cmpswap_x2` 150 与 `buffer_wbinvl1_vol` 100 就是 printf 缓冲）。
pa7 实测：基线 **886** 条、`<..,16>` **890** 条，`v_fmac_f32` **120 vs 87+33=120**、`ds_read_b128` 都是 24，
分数环都是 `v_mul_f32 + 7×v_fmac_f32`，只差末尾一条 `v_mul_f32`。**两个内核是同一段算术。**
"""
if "根因找到了：这七组 KL" not in s:
    io.open(P, "a", encoding="utf-8", newline="\n").write("\n" + add)
    print("plan: appended 十三")

q = io.open(P, encoding="utf-8").read()
q = q.replace("**410 条 / 已结 323 / 78.8%**", "**414 条 / 已结 327 / 79.0%**", 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(q)
print("plan denom -> 414/327")

# ---------------- memory ----------------
M = ".workbuddy/memory/2026-11-07.md"
mem = """
### W1039 根因（13:0x–13:2x）七组两两 KL 是同一个数 ⇒ 度量测的是混沌，不是精度

- **决定性数据**：ctl/C16/D32/F16D/DP4A 五者**两两** KL 全在 [0.0354, 0.0465]，跨度 1.31×。
  最硬的一行是 **C16 vs D32 = 0.04221**（两者扰动 1e-7 / 1e-5，若度量反映精度应 ≈0），
  与 **DP4A vs 基线 0.04130**（扰动 1e-2）一样大。⇒ 任意两臂等距 = **混沌映射**的统计距离。
- **机制**：1e-7 经 48 层残差放大到 1e-2，softmax 近 ties 翻边 ⇒ 任何非零扰动都落到同一宏观距离；
  逐位不变的臂（REDUCE12 / DPP）地板恰为 0。
- **外部（上网核）**：Yuan 2025 实测只改 batch/GPU 就带来最多 9% 准确率波动、响应长度差 9000 token；
  Thinking Machines 把批次相关内核列为主因；「80 层每层几个 ULP 足以翻 argmax」是共识。
- **⇒ 旧数值门（KL ≤ 0.0139 / top-1 ≥ 99% vs 逐位相同基线）对任何算术改动都必然 FAIL。**
  `P453`/`P456` 的 FAIL 是门的性质，不是 DP4A/F16D 的质量。
- **新判据（P470）**：地板臂 0.00000 + **同噪控制臂**（可证等价的算术重排，实测 0.0411）= 噪声地板；
  候选 ≤ 地板 ⇒ **不可判**；≥ 2× 地板才算有害。DP4A/F16D/F16Q 全在地板带内、彼此不可区分。
- **自我纠正（P469）**：`P463` 的「8 倍展平 7087 条」作废——那个 fatbin 比 .o 早 1 分钟，装的是 pa8 的 printf 版
  （`global_atomic_cmpswap_x2` / `buffer_wbinvl1_vol` 是 printf 缓冲）。pa7 实测 886 vs 890 条、`v_fmac` 120 = 87+33。
  **教训：dump 之前先核时间戳，别拿旧产物下结论。**
"""
s2 = io.open(M, encoding="utf-8").read()
if "七组两两 KL 是同一个数" not in s2:
    io.open(M, "a", encoding="utf-8", newline="\n").write(mem)
    print("memory: appended")

# ---------------- report ----------------
R = "albus/w1039/reply.md"
r = io.open(R, encoding="utf-8").read()
r = r.replace("**410 条 / 已结 323 / 78.8%**（本轮 +23：`P445`–`P467`）",
              "**414 条 / 已结 327 / 79.0%**（本轮 +27：`P445`–`P471`）", 1)

# retraction note in item 16
old16 = "**⇒ 「源码等价」不能当作「生成的代码等价」。** 我那条 bit-16 分支让整个内核展平了约 8 倍，"
new16 = ("**⇒ （本条已作废，见第 22 条）** 当时算出的「展平 8 倍」是**旧 fatbin** 的产物。**⇒ 「源码等价」不能当作「生成的代码等价」。** 我那条 bit-16 分支让整个内核展平了约 8 倍，")
assert old16 in r
r = r.replace(old16, new16, 1)

anchor = "**产物**：`albus/w1039/reply.md`（本件）"
add_r = """**21. 根因：这七组 KL 是同一个数——度量测的是模型的混沌，不是内核的精度（`P468`）**

把已落盘的五只臂（基线 + 四个开关）**两两**比，不看「谁离基线近」：

| 对比 | 两者的扰动差 | KL |
|---|---|---|
| ctl vs `CTLREAD` | **1e-7** | 0.04111 |
| ctl vs `F16Q` | 1e-5 | 0.04479 |
| ctl vs `F16D` | 1e-5 | 0.03798 |
| ctl vs `DP4A` | **1e-2** | 0.04130 |
| **`CTLREAD` vs `F16Q`** | 1e-7 vs 1e-5 | **0.04221** |
| **`DP4A` vs `F16D`** | 1e-2 vs 1e-5 | **0.03544** |
| `CTLREAD` vs `DP4A` | 1e-7 vs 1e-2 | 0.04650 |

**决定性的是 `CTLREAD` vs `F16Q` = 0.04221。** 两者都只差 1e-7~1e-5，如果这个度量反映**精度**，它们彼此应该 ≈0；
实测却和「差 1e-2 的 `DP4A` vs 基线」**一样大**。七个数挤在 [0.0354, 0.0465]、跨度 1.31× ——
**任意两臂等距**，这是混沌映射的统计距离，不是精度排序。

**机制**：1e-7 的扰动经 48 层残差放大到 O(1e-2)，在 softmax 上把近 ties 翻边；于是**任何非零扰动都落到同一个宏观距离**。
而 `REDUCE12` / `DPP` 两臂**逐位不变**（零扰动），地板才恰好是 0.00000。

**外部核实（不是猜）**：Yuan 等 2025《Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference》
实测仅改 batch / GPU 就让**准确率波动最多 9%、响应长度差 9,000 token**，根因是浮点非结合性；
Thinking Machines《Defeating Nondeterminism in LLM Inference》把批次相关内核行为列为主因；
多方一致：**80 层模型每层几个 ULP，足以在相当比例的 prompt 上翻转 argmax**。

**⇒ 旧数值门（对逐位相同的基线求 KL ≤ 0.0139 / top-1 ≥ 99%）对任何算术改动都不可能通过。**
`P453`/`P456` 的 FAIL 是**这道门的性质**，不是 DP4A / F16D 的质量。

**22. 撤回一条，并把门改造掉（`P469` / `P470` / `P471`）**

- **撤回**：第 16 条那个「`<..,16>` 被展平成 7087 条 / 408 个载入点」**是错的**。时间戳说明了原因：
  `.o` 是 **12:24**（pa7 重编），`fat.bin` 是 **12:23** —— dump 在重编之前，装的是 **pa8 的 printf 版**
  （`global_atomic_cmpswap_x2` 150 与 `buffer_wbinvl1_vol` 100 就是 printf 缓冲，我当时没认出来）。
  用 pa7 的真实 `.o` 重解：基线 **886** 条、`<..,16>` **890** 条；`v_fmac_f32` **120 vs 87+33 = 120**；
  `ds_read_b128` 都是 24；分数环都是 `v_mul_f32 + 7×v_fmac_f32`，只差末尾一条 `v_mul_f32`。**同一段算术。**
- **新门（`P470`）**：① 地板臂（同二进制同 argv 两容器）必须 **0.00000**；② **同噪控制臂**——一个可证等价的算术重排
  （本轮的 `CTLREAD`，ISA 与探针都证明只差 1e-7）给出**噪声地板 0.0411**；③ 候选 **≤ 地板 ⇒ 不可判**，
  **≥ 2× 地板才算有害**。按此，`DP4A` 0.0413 / `F16D` 0.0380 / `F16Q` 0.0448 **全在地板带内、彼此不可区分**。
- **对后续所有 R 的推论（`P471`）**：内核级改动只有两种可交付结论——**「逐位不变」**或**「不可测（须换下游判据）」**。
  把 0.04 当作「质量损失」去否决一个优化，就是**把模型的混沌记在优化头上**。

"""
assert anchor in r
r = r.replace(anchor, add_r + anchor, 1)
r = r.replace("`build_probe.sh` / `build_probe2.sh`。", "`build_probe.sh` / `build_probe2.sh` / `isa4.py`。", 1)
io.open(R, "w", encoding="utf-8", newline="\n").write(r)
print("report: %d chars" % len(r))
