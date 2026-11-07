# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 01:1x W929 · M3 结项：k8v8 对 prefill 零差异，且显存代价只有 P04 记录的 1/5（3 次重启）
- **实验**：两臂同带 `STRATA_PREFILL_TIMING=1`（观测成本对两臂相同）⇒ A=`k8v4`(7463 槽) vs B=`--kv int8`(=k8v8, 7223 槽)，同 prompt 词数各 3 次、token 数完全配对（6285/6380/6274）。
- **结果：prefill 零差异**。qsa attn **1202 → 1211 ms（+0.75%，噪声内）**；qsa proj +0.23%、gemm gate/up −0.11%、gemm down −0.09%、dequant −0.37%、GPU timeline 8475 → 8480 ms；**端到端 TTFT 9.218 vs 9.217 s**。
- **显存账纠正（重要）**：expert cache **7463 → 7223 = −240 槽 / 717 MiB**，**不是 P04 的 9761→8047（−1714 槽 / 3.8 GiB）**。原因：3.8 GiB 是旧 pack（2.31 MiB/槽、KV 未按需）年代；现 2.99 MiB/槽 + `kv ensured` 按需加载（有 ms 计时）。折合 ~66K tokens 而非 354K。按 3.2% 容量损失外推 decode 仅 **−1.1~2.3%**（非 −7.7~16.6%）。
- **判决 DONE_NEG**：k8v4 已过 needle 门 6/6（W770），用 decode 换更小的 KL（0.0416 vs 0.0704）不划算（decode 占 64–83%，W798）。但**记档 P258 为「长上下文重任务的便宜升级选项」——只花 717 MiB**。
- **两条副产品（比结论更重要，都指向「解包不是瓶颈」）**：
  - ① k8v4 的 V 每次 gather 都做 q4 反量化（`__half2float(blk->d)` + 4-bit 解包），换成纯 int8（零解包）后 attn **一点没变** ⇒ **4-bit 解包成本 ≈ 0**。这直接削弱 **R74(dot8)** 的一个卖点：dot8 的收益只剩「指令数减半」，而那个 W928 已算 = **3.22% 端到端 = 噪声门 3.2%** ⇒ R74 降权到 R69/R70/R65 之后，仅当离线 KL < 0.002 才动内核。
  - ② int8 多读 29.4% 字节（1056 vs 816 B/cell）而 attn 不变 ⇒ **attention 不是带宽受限**，与 W926 的 O(L^1.20) 拟合一致。
- **测量纪律 ⑧⑨（写进 W832）**：⑧**观测项代价必须做同状态 A/B** —— 启动时 `getenv` 静态初始化的开关不能热切换，代价只能记「未测出」；**禁止拿「热 cache 基线 vs 冷 cache 实验臂」的差当开关代价**（本轮误算 3.6%，实为 cache 冷热：8.901 是跑 26 分钟的热态，9.218/9.217 是刚重启的冷态）。⑨**跨代记录必须重测** —— P04 的 3.8 GiB 在当前 pack 下只有 717 MiB，差 5 倍；引用旧参数账的量化结论先核 pack 与槽大小。
- **生产**：config 回 **`51ef8837`**（k8v4、env 9 项、已撤 `STRATA_PREFILL_TIMING`）、engine `a97f4479`、7463 槽、920 MiB free、`/health ok`、restarts=0。3 次重启累计停机约 12 分钟。
- **队列**：`~~…~~ → ~~M3~~ → **R69** → **R70** → **R65** → **R74**（降权） → R49 → R50 → R30′`。进度 **158 条 / 95 已结 = 60.1%**，主线 **130 / 95 = 73.1%**。
- 产物：`deploy/W929_M3_K8V8_PREFILL.md`；`PROGRESS.tsv` M3(DONE_NEG) + R74 备注；`PARAM_REGISTER` **P258**；`W832` 纪律 ⑧⑨ + 队列。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
