import re, statistics as st, sys
sys.path.insert(0, "albus/r5")
from _rsh import sh
import base64

out = sh("base64 -w0 $(ls -t /home/albus/strata166/data/w802b_cpushare_*.txt | head -1)", t=60).strip()
txt = base64.b64decode(out).decode("utf-8", "replace")
open("albus/a9/w802b_cpushare.txt", "w", encoding="utf-8").write(txt)

cur = None
data = {}
for ln in txt.split("\n"):
    m = re.match(r"=== ARM ([AB]) share=(\w+) rep (\d)", ln)
    if m:
        cur = (m.group(2), int(m.group(3))); data[cur] = {"t": {}, "gpu": []}; continue
    m = re.match(r"T(\d) .*prompt_ms=\s*([0-9.]+)\s+decode_ms=\s*([0-9.]+)", ln)
    if m and cur: data[cur]["t"][int(m.group(1))] = (float(m.group(2)), float(m.group(3))); continue
    m = re.search(r"prefill timing: (\d+) tokens, GPU timeline (\d+) ms", ln)
    if m and cur and int(m.group(1)) < 1000: data[cur]["gpu"].append((int(m.group(1)), int(m.group(2))))

arms = {"0": [], "auto": []}
for (sh_, rep), d in sorted(data.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    arms[sh_].append(d)
for k in arms:
    print("share=%-4s n=%d  gpu_series=%s" % (k, len(arms[k]), [x["gpu"] for x in arms[k]]))
print()
for t in range(4):
    row = []
    for k, lab in (("0", "A(0)"), ("auto", "B(auto)")):
        p = [d["t"][t][0] for d in arms[k] if t in d["t"]]
        dec = [d["t"][t][1] for d in arms[k] if t in d["t"]]
        row.append((lab, st.median(p), sorted(round(x) for x in p), st.median(dec), sorted(round(x) for x in dec)))
    a, b = row[0], row[1]
    print("T%d prompt: %s 中位 %.1f %s | %s 中位 %.1f %s | Δ %+.1f%%" % (t, a[0], a[1], a[2], b[0], b[1], b[3-1], 100*(b[1]-a[1])/a[1]))
    print("   decode: %s 中位 %.1f | %s 中位 %.1f | Δ %+.1f%%" % (a[0], a[3], b[0], b[3], 100*(b[3]-a[3])/a[3]))
