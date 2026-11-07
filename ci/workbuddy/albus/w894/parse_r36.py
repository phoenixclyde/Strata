import re
import statistics
from pathlib import Path

root = Path(__file__).resolve().parent
stage = (root / "r36_stage.txt").read_text(encoding="utf-8", errors="replace").splitlines()
bench = (root / "r36_router_bench.txt").read_text(encoding="utf-8", errors="replace").splitlines()

rows = []
for line in stage:
    if "decode GPU stages" not in line:
        continue
    parts = line.split("|")
    gdn = re.search(r"GDN layers:.*?router\+plan\+bell\s+([0-9.]+)", parts[0])
    qsa = re.search(r"QSA layers:.*?router\+plan\+bell\s+([0-9.]+)", parts[1])
    total = re.search(r"total\s+([0-9.]+)\s+ms/window", parts[-1])
    win = re.search(r"over\s+(\d+)\s+windows", parts[-1])
    if gdn and qsa and total and win:
        rows.append((float(gdn.group(1)), float(qsa.group(1)), float(total.group(1)), int(win.group(1))))

routers = [a + b for a, b, _, _ in rows]
totals = [c for _, _, c, _ in rows]
print(f"stage_rows={len(rows)} windows={sum(w for *_, w in rows)}")
if rows:
    print("router median=%.3f mean=%.3f min=%.3f max=%.3f" % (
        statistics.median(routers), statistics.mean(routers), min(routers), max(routers)))
    print("total  median=%.3f mean=%.3f min=%.3f max=%.3f" % (
        statistics.median(totals), statistics.mean(totals), min(totals), max(totals)))
    print("share  median=%.2f%%" % (100 * statistics.median(routers) / statistics.median(totals)))
    sd = statistics.stdev(routers)
    print("router stdev=%.3f CV=%.2f%%  2xCV=%.3f ms" % (sd, 100 * sd / statistics.mean(routers), 2 * sd))

vals = {}
for line in bench:
    m = re.search(r"T 3\s+(.+?)\s+:\s+([0-9.]+) us per layer", line)
    if m:
        vals[m.group(1).strip()] = float(m.group(2))
for k, v in vals.items():
    print("bench %-22s %6.2f us/layer  chain=%6.2f ms/48layers" % (k, v, v * 48 / 1000))
if "mmvf+route+doorbell" in vals:
    base = vals.get("empty node", 0.0)
    chain = vals["mmvf+route+doorbell"]
    print("incremental over empty: mmvf=%.2f route=%.2f doorbell=%.2f chain=%.2f us/layer" % (
        vals.get("mmvf", 0) - base, vals.get("route", 0) - base, vals.get("doorbell", 0) - base, chain - base))
    print("chain_48=%.3f ms; production_median=%.3f ms; residual=%.3f ms" % (
        chain * 48 / 1000, statistics.median(routers), statistics.median(routers) - chain * 48 / 1000))
