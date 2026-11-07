import re, statistics as st, sys, base64
import sys as _s
_s.path.insert(0, "albus/r5")
from _rsh import sh

out = sh("base64 -w0 $(ls -t /home/albus/strata166/data/w801c_chat_*.txt | head -1)", t=60).strip()
txt = base64.b64decode(out).decode("utf-8", "replace")
open("albus/a9/w801c_chat.txt", "w", encoding="utf-8").write(txt)

cur = None
data = {}
for ln in txt.split("\n"):
    m = re.match(r"=== ARM (PROD|BASE7) rep (\d)", ln)
    if m:
        cur = (m.group(1), int(m.group(2))); data[cur] = {}; continue
    m = re.match(r"T(\d) ask=\s*(\d+)\s+read=(\d+)\s+reused=(\d+)\s+prompt_ms=\s*([0-9.]+)\s+decode_ms=\s*([0-9.]+)\s+tok_s=\s*([0-9.]+)", ln)
    if m and cur:
        data[cur][int(m.group(1))] = (float(m.group(5)), float(m.group(6)))

arms = {"PROD": [], "BASE7": []}
for (a, r), d in sorted(data.items()):
    if d:
        arms[a].append(d)
print("臂  rep  T0prompt T1prompt T2prompt T3prompt | T0dec T1dec T2dec T3dec")
for a in ("PROD", "BASE7"):
    for i, d in enumerate(arms[a], 1):
        print("%-5s %2d  %8.1f %8.1f %8.1f %8.1f | %6.1f %6.1f %6.1f %6.1f" % (
            a, i, d.get(0, (0,0))[0], d.get(1, (0,0))[0], d.get(2, (0,0))[0], d.get(3, (0,0))[0],
            d.get(0, (0,0))[1], d.get(1, (0,0))[1], d.get(2, (0,0))[1], d.get(3, (0,0))[1]))
print("\n--- 中位与差（PROD 相对 BASE7）---")
for t in range(4):
    for k, lab in ((0, "prompt"), (1, "decode")):
        p = [d[t][k] for d in arms["PROD"] if t in d]
        b = [d[t][k] for d in arms["BASE7"] if t in d]
        if not p or not b: continue
        mp, mb = st.median(p), st.median(b)
        print("T%d %-6s PROD n=%d 中位 %7.1f %s | BASE7 n=%d 中位 %7.1f %s | Δ %+6.1f%%" % (
            t, lab, len(p), mp, sorted(round(x,1) for x in p), len(b), mb, sorted(round(x,1) for x in b),
            100*(mp-mb)/mb))
