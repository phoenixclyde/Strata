# -*- coding: utf-8 -*-
"""W942b: R60/R61 are closed -> set their done flag (col 6) so the ledger's denominator moves."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
with io.open(P, encoding="utf-8", newline="") as f:
    lines = f.read().split("\n")

out, changed = [], []
for ln in lines:
    if "\t" in ln:
        f8 = ln.split("\t")
        if len(f8) >= 9 and f8[1] in ("R60", "R61") and f8[6] != "1":
            f8[6] = "1"; changed.append(f8[1]); ln = "\t".join(f8)
    out.append(ln)

with io.open(P, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(out))
print("done set:", changed)
