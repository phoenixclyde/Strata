#!/usr/bin/env python3
"""W945: per-kernel PMC summary for several counters (duration-weighted)."""
import csv, glob, sys, collections

d = sys.argv[1] if len(sys.argv) > 1 else "/data/w945q51"
rows = []
files = [f for f in glob.glob(d + "/**/*.csv", recursive=True) if "counter_collection" in f]
for f in files:
    with open(f, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                dur = int(r["End_Timestamp"]) - int(r["Start_Timestamp"])
                v = float(r["Counter_Value"])
            except (KeyError, ValueError):
                continue
            rows.append((r["Kernel_Name"], r["Counter_Name"], dur, v))

if not rows:
    print("NO ROWS", files)
    sys.exit(1)

agg = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
total = 0
for name, cnt, dur, v in rows:
    a = agg[name][cnt]
    a[0] += dur
    a[1] += v * dur
    if cnt == "VALUBusy":
        total += dur

print("files=%d rows=%d" % (len(files), len(rows)))
for name, per in sorted(agg.items(), key=lambda kv: -max(x[0] for x in kv[1].values())):
    dur = max(x[0] for x in per.values())
    print("\n%s" % (name[:110]))
    print("  duration %.2f ms   share %.1f%%" % (dur / 1e6, 100.0 * dur / total if total else 0))
    for cnt in ("VALUBusy", "MemUnitStalled", "FetchSize"):
        if cnt in per and per[cnt][0]:
            avg = per[cnt][1] / per[cnt][0]
            print("  %-16s %.2f%s" % (cnt, avg, " (weighted mean)" if cnt != "FetchSize" else " (per-dispatch bytes)"))
