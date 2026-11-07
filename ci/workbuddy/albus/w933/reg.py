# -*- coding: utf-8 -*-
"""W933: R76 结项 + P259 补注 + 队列"""
import io, os

D = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "deploy"))

p = os.path.join(D, "PROGRESS.tsv")
lines = io.open(p, encoding="utf-8").read().split("\n")
for i, l in enumerate(lines):
    f = l.split("\t")
    if len(f) == 10 and f[1] == "R76":
        f[6] = "1"
        f[7] = "DONE"
        f[8] += (
            " 【W933 实测 2026-11-04 08:4x-09:1x｜4 次重启｜**保留 auto:16384**】"
            "①**实测复用粒度 = chunk**：`DOC(30K)+Q_A` → `DOC+追加+Q_B`，8192 模式 turn2 复用 **24576**（3 chunk）、"
            "read 728、耗时 **2.63 s**；16384 模式复用 **16384**（1 chunk）、read 8920、耗时 **12.56 s** ⇒ 单次 +9.9 s（4.8×）。"
            "（turn1 本身 16384 快 7.5%：32.1 vs 34.5 s，与 W932 的 32K +5% 一致。）"
            "②**纠正一个中间错误**：按 `0<r<t-16` 统计得「部分复用 19.1%」，按最坏情况估「平均多读 6874 token ≈ 8.6 s」"
            "—— **错**。大部分是**正常多轮**（turn2=turn1+回答+问句，r=turn1 长度<t），走 **conversation cache**（整块、与 chunk 无关）。"
            "正确口径 = `r % 8192 == 0 && t-r > 64`（chunk 对齐的部分前缀）⇒ **13/3000 = 0.4%**（其中约一半是本次测试自身）。"
            "切 16384 后这批多读 90,112 token（平均 6931 = 8.7 s），**摊到全体 3000 请求只有 30 token ≈ 0.04 s**。"
            "③**新发现：prompt cache 只缓存完整 chunk** —— 6667 token 的部分前缀测试在 **8192 模式下也复用 0**"
            "（reused=0, read=6667, 9610 ms）⇒「切 16384 会让短 prompt 失去复用」这个担心不成立（本来就没有）。"
            "多轮 6580 能复用 99.68% 靠的是 conversation cache。"
            "**判决**：收益 +2.2% prefill（W932）vs 代价 0.04 s/请求 ⇒ **保留**。"
            "**保留条件**：若将来出现「同一 30K 文档改几个字反复问」的用法，需重评（那时 auto/8192 更好）"
        )
        lines[i] = "\t".join(f)
        print("R76 -> DONE")
io.open(p, "w", encoding="utf-8").write("\n".join(lines))

# P259 补注
q = os.path.join(D, "params", "PARAM_REGISTER.tsv")
pr = io.open(q, encoding="utf-8").read().split("\n")
for i, l in enumerate(pr):
    f = l.split("\t")
    if f and f[0] == "P259":
        f[10] += (
            " **【W933 补注 2026-11-04 09:1x｜R76 结项】**复用粒度实测 = chunk 大小：30K 文档追加场景下，"
            "8192 模式 turn2 复用 24576（2.63 s）、16384 模式复用 16384（12.56 s），单次 +9.9 s。"
            "但**真正的部分前缀只占负载 0.4%**（13/3000，按 `reused%8192==0 && t-reused>64` 识别；"
            "此前误判「19.1%」是把正常多轮算进来了），摊到全体仅 **0.04 s/请求** ⇒ 保留。"
            "**副产物**：prompt cache 只缓存**完整 chunk**（6667 token 的部分前缀在 8192 下也复用 0）；"
            "多轮复用走的是 conversation cache（整块、与 chunk 无关）。"
            "**保留条件**：出现「同一长文档改几个字反复问」的用法时重评"
        )
        pr[i] = "\t".join(f)
        print("P259 note appended")
        break
io.open(q, "w", encoding="utf-8").write("\n".join(pr))

# 队列
r = os.path.join(D, "W832_OPT_PLAN_V2.md")
s = io.open(r, encoding="utf-8").read()
ls = s.split("\n")
for i, l in enumerate(ls):
    if l.startswith("> **执行顺序（2026-11-04"):
        ls[i] = (
            "> **执行顺序（2026-11-04 09:1x 修，`W933`）：~~R59~~ → ~~R67~~ → ~~R66~~ → ~~R68~~ → ~~R72~~ "
            "→ ~~R61~~ → ~~R60~~ → ~~R58~~ → ~~R63~~ → ~~R64~~ → ~~R73~~ → ~~M3~~ → ~~R69~~ → ~~R70"
            "（已采纳 auto:16384）~~ → ~~R75~~ → ~~R76（部分前缀代价 0.04 s/请求，保留 16384）~~ → "
            "**R65**（0.2.10 rebase 只读评估） → **R74**（W4A4 精度门） → R49 → R50 → R30′**"
        )
        print("queue updated")
        break
io.open(r, "w", encoding="utf-8").write("\n".join(ls))
print("done")
