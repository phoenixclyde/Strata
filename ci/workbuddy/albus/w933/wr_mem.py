# -*- coding: utf-8 -*-
import io, os
M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory"))
p = os.path.join(M, "2026-11-04.md")

sec = """
## 09:1x W933 · R76 结项：`auto:16384` 的部分前缀代价只有 0.04 s/请求，保留（4 次重启）
- **实测复用粒度 = chunk**：`DOC(30K)+Q_A` → `DOC+追加+Q_B`。8192 模式 turn2 复用 **24576**（3 chunk）、read 728、**2.63 s**；16384 模式复用 **16384**（1 chunk）、read 8920、**12.56 s** ⇒ 单次 **+9.9 s（4.8×）**。turn1 本身 16384 快 7.5%（32.1 vs 34.5 s）。
- **纠正我自己的统计口径错误**：按 `0<r<t-16` 得「部分复用 19.1%」，按最坏估「平均多读 6874 token ≈ 8.6 s」——**错**。大部分是**正常多轮**（turn2=turn1+回答+问句，r=turn1 长度<t），走 conversation cache。正确口径 `r%8192==0 && t-r>64` ⇒ **13/3000 = 0.4%**（约一半还是本次测试自身）⇒ 摊到全体 **30 token ≈ 0.04 s/请求**。
- **两条复用路径（本轮确认）**：①**conversation cache**（整块快照）—— turn2 完整包含 turn1 时触发，**与 chunk 无关**（多轮实测 99.68%）；②**prompt cache** —— 只有部分前缀重合时触发，**按 chunk 对齐**（所以切 16384 会少复用）。
- **新发现：prompt cache 只缓存完整 chunk** —— 6667 token 的部分前缀测试在 **8192 模式下也复用 0**（reused=0, read=6667, 9610 ms）⇒「切 16384 会让短 prompt 失去复用」这个担心不成立（本来就没有）。8580 的多轮能复用 99.68% 靠的是 conversation cache。
- **判决：保留 `auto:16384`** —— 收益 +2.2% prefill（W932）vs 代价 0.04 s/请求。**保留条件**：若出现「同一 30K 文档改几个字反复问」的用法，需重评（那时 auto/8192 更好）。
- **一个反直觉的对称性**：chunk 越大，单发 prefill 越快（GEMM 的 M 越大），但**部分前缀的复用损失也越大**（对齐粒度变粗）——同一个原因的两面。
- **生产**：config `fcf4df5b`、`--prefill auto:16384`、engine `a97f4479`、borrows 2606、expert cache 7463、VRAM free 920 MiB、`/health ok`、restarts=0。
- **队列**：`~~…~~ → ~~R76~~ → **R65**（0.2.10 rebase 只读评估） → **R74**（W4A4 精度门） → R49 → R50 → R30′`。进度 **160 条 / 99 已结 = 61.9%**，主线 **132 / 99 = 75.0%**。
- 产物：`deploy/W933_R76_PARTIAL_PREFIX.md`；`PROGRESS.tsv` R76(DONE)；`PARAM_REGISTER` P259 补注；`W832` 队列；探针 `albus/w933/partprefix.py`（已参数化为 PP_WORDS/PP_SEED）。
"""
with io.open(p, "a", encoding="utf-8") as f:
    f.write(sec)
print("ok", len(sec))
