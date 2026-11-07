#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039: put the report back into the shape every normal round used (w1021-w1037).

What drifted, measured against w1034/w1037:
  * section 三 had grown into a 6-row table where the older reports had one sentence with
    重启 / 停机 / 回滚 / 装机 inline;
  * the body used `## T1 .. T10`, i.e. a THIRD numbering scheme (the quartet uses 一二三四, the
    older bodies used `**1. ...**`), which is what makes "§三" ambiguous when quoting the report.
Fix: one sentence for 三, `## 正文` + `**n. ...**` for the body, exactly like w1034.
"""
import io
import re

P = "albus/w1039/reply.md"
s = io.open(P, encoding="utf-8").read()

# ---- 1. section 三: table -> one sentence -----------------------------------------------
old3_start = s.index("**三、本次落生产**")
old3_end = s.index("**四、进度**")
new3 = (
    "**三、本次落生产** — 引擎：**无净变更**（在产全程 `b12180`，每臂结束都停容器还原 config、起容器、"
    "核对 `exe` 与 md5 回 `5e9b81e2…`）；**重启 11 次、停机 1779 s、回滚 0 次、装机 0 次**。六个窗口依次是："
    "① pa3 零效果 09:02–09:16（3 次 / 129 s）② pa4 负收益 09:18–09:32（3 次 / 135 s）"
    "③ pa5 救法 09:55–10:04（2 次 / 90 s）④ 数值门试跑 10:13–10:14（1 次 / 52 s）"
    "⑤ 数值门 int8 10:18–10:29（1 次 / 683 s）⑥ 数值门 fp16 10:49–11:00（1 次 / 690 s）；"
    "**最长单次停机 690 s**（数值门三臂独占 GPU）。\n\n"
)
s = s[:old3_start] + new3 + s[old3_end:]

# ---- 2. body: `## Tn xxx` -> `**n. xxx**`, `### Tn xxx` -> `**n.m xxx**` ------------------
head, sep, body = s.partition("\n---\n")
n = 0
sub = 0
out = []
for ln in body.split("\n"):
    m = re.match(r"^## T(\d+)\s+(.*)$", ln)
    if m:
        n += 1
        sub = 0
        out.append("**%d. %s**" % (n, m.group(2)))
        continue
    m = re.match(r"^### T(\d+)\s+(.*)$", ln)
    if m:
        sub += 1
        out.append("")
        out.append("**%d.%d %s**" % (n, sub, m.group(2)))
        continue
    out.append(ln)
body = "\n".join(out)

# body must open with the plain `## 正文` marker, as in w1031/w1034
body = body.lstrip("\n")
if not body.startswith("## 正文"):
    body = "## 正文\n\n" + body

io.open(P, "w", encoding="utf-8", newline="\n").write(head + sep + body)
print("restored: 三 is one sentence, body is 正文 + %d numbered blocks" % n)
for ln in (head + sep + body).split("\n"):
    if ln.startswith("**") and re.match(r"^\*\*\d+\.", ln):
        print("   ", ln[:70])
