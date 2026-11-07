# -*- coding: utf-8 -*-
"""[W863] Quantify the plan: how many items exist, how many are settled, how many moved this round.

Single source: deploy/PROGRESS.tsv.  Columns: block id item source kind count done status note ref
`count` is the weight (a dead-block pool is 28 items, not 1), `done` is how many of them are settled,
so the headline numbers are weighted, not row counts.
"""
import collections
import csv
import os

P = r"D:\workbuddy_space\strata_ws\deploy\PROGRESS.tsv"

rows = []
with open(P, encoding="utf-8") as f:
    lines = [l for l in f if not l.startswith("#") and l.strip()]
rdr = csv.DictReader(lines, delimiter="\t")
for r in rdr:
    try:
        r["count"] = int(r["count"] or 1)
        r["done"] = int(r["done"] or 0)
    except ValueError:
        r["count"], r["done"] = 1, 0
    rows.append(r)

by_status = collections.OrderedDict()
for r in rows:
    s = (r["status"] or "?").strip()
    d = by_status.setdefault(s, {"rows": 0, "count": 0, "done": 0})
    d["rows"] += 1
    d["count"] += r["count"]
    d["done"] += r["done"]

tot_rows = len(rows)
tot_count = sum(r["count"] for r in rows)
tot_done = sum(r["done"] for r in rows)

print("=" * 78)
print("PROGRESS.tsv  %s" % P)
print("=" * 78)
print("rows=%d   weighted items=%d   settled(done)=%d   open=%d"
      % (tot_rows, tot_count, tot_done, tot_count - tot_done))
print()
print("%-12s %6s %8s %8s %8s" % ("status", "rows", "weight", "done", "open"))
for s, d in sorted(by_status.items(), key=lambda kv: -kv[1]["count"]):
    print("%-12s %6d %8d %8d %8d" % (s, d["rows"], d["count"], d["done"], d["count"] - d["done"]))

settled = sum(d["count"] for s, d in by_status.items() if s in ("DONE", "DONE_NEG", "NA"))
adopted = sum(d["count"] for s, d in by_status.items() if s == "DONE")
rejected = sum(d["count"] for s, d in by_status.items() if s == "DONE_NEG")
print()
print("settled rate  = %d/%d = %.1f%%" % (settled, tot_count, 100.0 * settled / tot_count))
if settled:
    print("adopt rate    = %d/%d settled = %.1f%%   (DONE_NEG = %d)"
          % (adopted, settled, 100.0 * adopted / settled, rejected))
print()
print("--- open items (the actual remaining work) ---")
for r in rows:
    if r["status"] in ("OPEN", "INFLIGHT", "BLOCKED"):
        print("  %-3s %-42s %-9s %s" % (r["id"], r["item"][:42], r["status"], r["block"][:14]))

print()
print("--- this round's rows (R22..R26) ---")
for r in rows:
    if r["id"] in ("R22", "R23", "R24", "R25", "R26") or r["id"].startswith("R2"):
        print("  %-4s %-44s %-9s w=%s done=%s  %s"
              % (r["id"], r["item"][:44], r["status"], r["count"], r["done"], (r["note"] or "")[:60]))
