import io

pairs = [
    ("deploy/W832_OPT_PLAN_V2.md", "**386 条 / 已结 302 / 78.2%**（W1038 校正", "**387 条 / 已结 302 / 78.0%**（W1038 校正"),
    ("albus/w1038/reply.md", "**386 条 / 已结 302 / 78.2%**（本轮 +3：`P442` / `P443` / `P444`）",
     "**387 条 / 已结 302 / 78.0%**（本轮 +4：`P442` / `P443` / `P444` / `R104`）"),
]
for p, a, b in pairs:
    s = io.open(p, encoding="utf-8").read()
    if a in s:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(a, b, 1))
        print("ok", p)
    else:
        print("MISS", p, a[:40])
