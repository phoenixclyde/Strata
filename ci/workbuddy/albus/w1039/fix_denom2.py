import io
import re

pairs = [
    ("deploy/W832_OPT_PLAN_V2.md", "**391 条 / 已结 306 / 78.3%**（W1039 校正", "**393 条 / 已结 308 / 78.4%**（W1039 校正"),
    ("albus/w1039/reply.md", "**391 条 / 已结 306 / 78.3%**（本轮 +4：`P445`–`P448`）",
     "**393 条 / 已结 308 / 78.4%**（本轮 +6：`P445`–`P450`）"),
]
for p, a, b in pairs:
    s = io.open(p, encoding="utf-8").read()
    if a in s:
        io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(a, b, 1))
        print("ok", p)
    else:
        # try the loose form for the plan (denominator may have moved during the round)
        m = re.search(r"\*\*\d+ 条 / 已结 \d+ / [\d.]+%\*\*（W1039 校正", s)
        if m:
            s = s[:m.start()] + "**393 条 / 已结 308 / 78.4%**（W1039 校正" + s[m.end():]
            io.open(p, "w", encoding="utf-8", newline="\n").write(s)
            print("loose ok", p)
        else:
            print("MISS", p)
