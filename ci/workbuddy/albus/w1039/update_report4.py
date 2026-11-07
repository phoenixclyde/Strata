#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: probe #2 and the decision (R103 attn closed as unmeasurable, R104 to the front)."""
import io

P = "albus/w1039/reply.md"
s = io.open(P, encoding="utf-8").read()

old4 = "**四、进度** — **408 条 / 已结 321 / 78.7%**（本轮 +21：`P445`–`P465`）。"
new4 = "**四、进度** — **410 条 / 已结 323 / 78.8%**（本轮 +23：`P445`–`P467`）。"
assert old4 in s
s = s.replace(old4, new4, 1)

# queue line in 四
oldq = "队列：`R104`（`--kv-grow`）→ `R103` → `R95`"
newq = "队列：`R104`（`--kv-grow`）→ ~~`R103`~~（attn 一支结案：本季不可测）→ `R95`"
assert oldq in s
s = s.replace(oldq, newq, 1)

anchor = "**产物**：`albus/w1039/reply.md`（本件）"
assert anchor in s
add = """**20. 抵消放大也救不了算术；于是 R103 的 attn 一支结案为「本季不可测」（`P466` / `P467`）**

上一版留了一个口子：也许真实模型的 q 带大直流、k 码和近零，强抵消会把 1e-7 放大。**不估，直接构造该载荷测：**

| 载荷 | 抵消因子 | 部分和 max\\|Δ\\| | 分数 max\\|Δ\\| | 分数 max rel |
|---|---|---|---|---|
| 随机 q / 随机码 | 65.0 | 2.98e-08 | 1.19e-07 | 4.2e-06 |
| **q 直流 8 / 码值逐维正负配平** | 47.4 | 7.15e-07 | **1.91e-06** | **9.3e-05** |

放大确实存在（22 倍），但**绝对值仍停在 1e-6**；而改一个 argmax 需要 **0.19 nat** 的中位判决间隔（第 8 条）。
**差 2–3 个数量级。** 至此 fp32 结合次序（手写读、末尾乘 scale、展平重排）全部出局。

**七条实测合起来，没有一条能把 0.04 钉在指令或我们那几行代码上**：只动归约的两臂逐位相同（第 13/17 条）；
动 per-lane 部分和的四臂一律 ≈0.04、两两相关只有 0.50–0.65；探针说读法与算术只差 1e-6（第 19/20 条）；
ISA 说 C16 那条分支被展平 8 倍（第 16 条）；而引擎里的三条仪表通道全堵（`printf` 被工具吞、`--cuda-device-only` 被 host-only 符号挡、
`.hip_fatbin` 只能看规模）。

**⇒ 判决改了：`P453` / `P456` 不是「判否」，是「没测准」，一律作废。** 处置三条：
① `R103` 的 attn 一支**结案为本季不可测**；② `pa5`–`pa8` **不装机**，开关默认关；③ **队列首改成 `R104`**
（`--kv-grow`，770+ 专家槽 ≈ **+10%**，零代码、不碰数值面）。

**一个外部对照（不猜）**：bittide 在 RDNA3 上用打包 int8 K + `sudot4` 的实测是 **KLD 0.00455 / 同 top-1 97.06%**，
比我们四臂的 0.041 好一个数量级 ⇒ **「int8 点积做不到低 KL」不成立**，问题在我们的测量手段，不在指令。

**这一轮真正的产出不是那个 −11%，而是一条纪律**：引擎里的数值问题，先问「我看得见吗」。
看不见就写独立 HIP 探针——几十 KB、1 秒、可与生产共用 GPU、`printf` 直接出 stdout。
那次 782 s 的白烧，就是没先问这一句。

"""
s = s.replace(anchor, add + anchor, 1)
s = s.replace("`gate7.sh` / `t_probe.cu` / `build_probe.sh`。",
              "`gate7.sh` / `t_probe.cu` / `t_probe2.cu` / `build_probe.sh` / `build_probe2.sh`。", 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("report: %d chars" % len(s))
