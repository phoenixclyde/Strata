# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 01:4x W931 · R70 结项：chunk 上限是**倒 U**，机制是「chunk 在抢 expert cache」（7 次重启）
- **数据**（同 prompt 词数各 2–3 次，CV 0.1–1.4%）：32K prompt —— 8192(4chunk) **40.548 s** / **16384(2chunk) 38.542 s(−4.95%)** / 32768(1chunk) 39.263 s(−3.17%)。跨长度：16K **20.775→20.233(−2.61%)**、**64K 71.130→76.557(+7.63%，变慢)**、6.4K 8.901→8.764(−1.5%≈0)。
- **机制（本轮最大收获）**：`--prefill auto` 的定义是「**expert cache 能借到的最大 chunk**」，日志 borrows **1578 / 2606 / 4667 slots**（4.62/7.62/**13.64** GiB，占 7463 的 21.1/34.9/**62.5%**）⇒ **chunk 与 expert cache 抢同一批槽**。短 prompt 因减少 chunk 切换而赢，长 prompt 因常驻专家变少、stream 变多而亏。交叉点在 32K–64K 之间，**不存在单一最优值**。
- **不采纳（净值核算）**：真实负载 6517 样本 —— ≤8192 占 **60.8%**(0)、8–16K 2.2%(0)、16–32K 5.8%(−5%)、32–48K 1.6%、48–64K 4.7%、**>64K 24.8%(+7.6%)** ⇒ **加权 ≈ +1.5% 变慢**。
- **顺带纠正一个持续很久的先验**：我一直用 6.4K prompt 做基准，以为那是主要场景 —— **那是我的测试 prompt**。真实负载：中位 **4378**、p90 **106301**、max 206226、**39.2% 超过 8192**、>64K 占 24.8%。以后做 prefill 实验必须按这个分布加权，不能只看单一长度。
- **新假设已立 R75**：①R66 三 opt-in 单独 DONE_NEG（borrows 1578→1226 −22.3%，但 prefill −0.23% 噪声内）—— 当时因 chunk=8192 不是瓶颈；②`auto:16384` 单独净亏。**组合假设**：chunk=16384 时 borrows 2606(+65%) 正是长 prompt 变慢的直接原因，R66 压 22% ⇒ 约 2030，或可让 16384 在 >64K 上也不亏，白拿 16–32K 的 −5%。判据：borrows 降到 ~2030（路径断言）+ 64K 不高于 71.130 s + 16–32K 保住 −2.6~−5%。
- **`auto:32768` 不要用**：借 62.5% cache，任何长度都更慢。
- **生产**：config 回 **`51ef8837`**（逐字节，`--prefill auto`、`--kv k8v4`、env 9、args 33）、engine `a97f4479`、7463 槽、borrows 1578、VRAM free 920 MiB、`/health ok`、restarts=0。7 次重启累计停机约 30 分钟。
- **队列**：`~~…~~ → ~~R70~~ → **R75** → **R65** → **R74** → R49 → R50 → R30′`。进度 **159 条 / 97 已结 = 61.0%**，主线 **131 / 97 = 74.0%**。
- 产物：`deploy/W931_R70_CHUNK_SCAN.md`；`PROGRESS.tsv` R70(DONE_NEG) + R75(OPEN)；`PARAM_REGISTER` **P259**；`W832` 队列。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
