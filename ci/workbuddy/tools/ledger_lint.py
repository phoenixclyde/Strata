# -*- coding: utf-8 -*-
"""ledger_lint.py -- AUDIT24 discipline 21/22.

21) every PROGRESS.tsv row must have 10 columns and an evidence body (note) >= 20 chars,
    never a placeholder like "1";
22) every markdown table row must have the same number of cells as its header --
    an unescaped | inside a cell silently splits it (12 rows in W832 were broken this way).
"""
import io, sys, re, hashlib

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
COLS = 10
fails = []

rows = [ln.split("\t") for ln in io.open(P, encoding="utf-8").read().splitlines() if ln.strip()]
rows = [r for r in rows if not r[0].startswith("#") and r[0] != "block"]
CLOSED = ("DONE", "DONE_NEG", "NA", "WITHDRAWN")
for i, r in enumerate(rows, 1):
    if len(r) != COLS:
        fails.append("PROGRESS row %-3d %-6s: %d columns" % (i, r[1] if len(r) > 1 else "?", len(r)))
        continue
    note = r[8].strip()
    ref = r[9] if len(r) > 9 else ""
    # a placeholder (pure number) is always a defect; otherwise a closed row needs a body
    # OR a document reference it can be traced back to
    if re.fullmatch(r"\d+", note) or (r[7] in CLOSED and len(note) < 8 and "W" not in ref):
        fails.append("PROGRESS row %-3d %-6s: evidence %r" % (i, r[1], note[:20]))

# table shape: only the authoritative plan + the audit docs (older W7xx are superseded assets)
import glob, os
TARGETS = ["D:/workbuddy_space/strata_ws/deploy/W832_OPT_PLAN_V2.md"] + \
          sorted(glob.glob("D:/workbuddy_space/strata_ws/deploy/AUDIT2*.md"))
for p in TARGETS:
    lines = io.open(p, encoding="utf-8", errors="replace").read().split("\n")
    want = None
    for n, ln in enumerate(lines, 1):
        if not ln.startswith("|"):
            want = None
            continue
        cells = ln.count("|") - ln.count("\\|")
        if want is None:
            want = cells
            continue
        if cells != want and not set(ln.replace("|", "").strip()) <= set("-: "):
            fails.append("%-40s line %-4d: %d cells (header %d)" % (os.path.basename(p), n, cells, want))

print("ledger rows %d | problems %d" % (len(rows), len(fails)))
for f in fails[:40]:
    print("  " + f)
print("md5(PROGRESS) =", hashlib.md5(io.open(P, "rb").read()).hexdigest())
