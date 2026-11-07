import io

P = ".workbuddy/memory/2026-11-07.md"
ADD = """
### W1040 深挖（09:44–10:0x）DP4A 为什么反而慢：付了「热路径 QDQ」的钱

- **预算（源码常数）**：`CHUNK=64`/`THREADS=256`/`G=12`/`NSC=4`/`top_k=2048` ⇒ **每 query 64 个块**（32 chunk × 2 KV 头）。量化段 `if (t < G*NSC)` 只用 **48/256 线程**，每线程串行 64 amax + 64 div/cvt ≈400 条，其余 208 线程等 `__syncthreads`。
- **分数段确实省**：每 cell 每 lane 基线 ≈130（12×8 FMA + 反量化 + reduce12），dp4a ≈85 ⇒ 省 35%；但 +400 周期量化后每块 1080 vs 1040 ⇒ 净 +4%，实测 attn +6.8%。
- **关键比值**：每 8 MAC，dot4 只省 3 条（2 dot4 + cvt + 2 mul 收尾 vs 8 fma）——4× 算术密度被「每头一次收尾」吃回 1.6×；再把量化摊到 8 cell（56 条/cell）就转负。
- **对照 iacop `fattn-q8.cuh`**：`quantize_Q_to_shared` **全线程**、一块摊 `nbatch_K`(128–256) 个 key、KV 原生 Q8_0 不需反量化——三处都比我们好。
- **外证（skyne98，同代 MI50 实测）**：热循环 QDQ 的 int8-dot4 **2.00 TOPS vs fp32 5.95（0.34×）**；摊薄复用后 dot4 21.7 vs 13.0（1.67×）。原文：conversion paid every use ⇒ dot 不划算。同站 dot 吞吐实测 sdot4 21.7–22.3 TOPS ⇒ **硬件没打折**。
- **天花板**：分数段砍 45% ⇒ 总 prefill 16K 仅 **−3.5%**，小于 R104 的 +10% ⇒ **B1/B2 收口 DONE_NEG**。
- **判据（可复用）**：引入 int8 dot 前先算「每 8 MAC 的净节省 − 每 cell 摊到的量化成本」，为负就别上；或先问「转换被摊薄了几次」。
"""
with io.open(P, "a", encoding="utf-8", newline="\n") as fh:
    fh.write(ADD)
print("mem appended", len(ADD))
