import re, io

p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log"
rows = []
for line in io.open(p, errors="replace"):
    if "engine started" not in line:
        continue
    m = re.search(r"2026-\d\d-\d\d \d\d:\d\d", line)
    ts = m.group(0) if m else "?"
    m2 = re.search(r"resident-budget-gib (\d+)", line)
    m3 = re.search(r"packs/([A-Za-z0-9_\-]+)", line)
    m4 = re.search(r"--prefill ([a-z0-9:]+)", line)
    rows.append((ts, m2.group(1) if m2 else "-", m3.group(1) if m3 else "?", m4.group(1) if m4 else "?"))

print("total starts:", len(rows))
prev = None
for ts, rb, pack, pre in rows:
    key = (rb, pack, pre)
    if key != prev:
        print("%s  resident=%-3s pack=%-12s prefill=%s" % (ts, rb, pack, pre))
        prev = key
print("...")
for r in rows[-3:]:
    print("LAST", r)
