#!/usr/bin/env python3
"""Aggregate rocprofv3 PMC csv: VALUBusy weighted by kernel duration, per kernel name."""
import csv, glob, sys, collections

d = sys.argv[1] if len(sys.argv) > 1 else "/data/w941pmc"
files = glob.glob(d + "/**/*.csv", recursive=True)
rows = []
for f in files:
    if "counter_collection" not in f:
        continue
    with open(f, newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("Counter_Name") != "VALUBusy":
                continue
            try:
                dur = int(r["End_Timestamp"]) - int(r["Start_Timestamp"])
                v = float(r["Counter_Value"])
            except (KeyError, ValueError):
                continue
            rows.append((r["Kernel_Name"], dur, v))

if not rows:
    print("NO ROWS in", files)
    sys.exit(1)

agg = collections.defaultdict(lambda: [0, 0.0, 0])  # dur, val*dur, n
for name, dur, v in rows:
    a = agg[name]
    a[0] += dur
    a[1] += v * dur
    a[2] += 1

total = sum(a[0] for a in agg.values())
print("files=%d rows=%d kernels=%d total_kernel_ms=%.1f" % (len(files), len(rows), len(agg), total / 1e6))
print("%-9s %-7s %-7s %s" % ("share%", "ms", "VALUBusy", "kernel"))
for name, (dur, vd, n) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:25]:
    short = name if len(name) < 96 else name[:93] + "..."
    print("%8.2f%% %8.1f %7.1f%% %s  (n=%d)" % (100.0 * dur / total, dur / 1e6, vd / dur, short, n))

mmq = [kv for kv in agg.items() if "mul_mat_q" in kv[0] or "mmq" in kv[0].lower()]
if mmq:
    dur = sum(kv[1][0] for kv in mmq)
    vd = sum(kv[1][1] for kv in mmq)
    print("\nMMQ family: share=%.2f%% time=%.1f ms VALUBusy=%.1f%% (kernels=%d)" % (100.0*dur/total, dur/1e6, vd/dur, len(mmq)))
    for name, (d2, v2, n) in sorted(mmq, key=lambda kv: -kv[1][0])[:8]:
        print("  %6.2f%% %8.1f ms %6.1f%% %s (n=%d)" % (100.0*d2/total, d2/1e6, v2/d2, name[:88], n))
