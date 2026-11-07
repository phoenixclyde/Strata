# -*- coding: utf-8 -*-
"""ledger_lint caught 30 rows with 9 columns (missing the trailing ref column).

These were appended by W98x/W99x patch scripts that built a 9-element row while
PROGRESS.tsv has 10 columns (block id item source kind count done status note ref).
Add an explicit '-' ref instead of leaving a ragged table.
"""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().splitlines()
out, fixed = [], 0
for l in lines:
    c = l.split("\t")
    if len(c) == 9:
        c.append("-")
        l = "\t".join(c)
        fixed += 1
    out.append(l)
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out) + "\n")
print("fixed 9-column rows:", fixed)
