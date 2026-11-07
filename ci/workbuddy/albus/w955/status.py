# -*- coding: utf-8 -*-
"""R90 -> INFLIGHT (S1/S2 done, S3/S4 pending); refresh ledger md5; sanity numbers."""
import io, csv, subprocess

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
rows = list(csv.reader(io.open(P, encoding="utf-8").read().splitlines(), delimiter="\t"))
for r in rows:
    if len(r) > 7 and r[1] == "R90" and r[7] == "OPEN":
        r[7] = "INFLIGHT"
        print("R90 -> INFLIGHT")
io.open(P, "w", encoding="utf-8", newline="").write("\n".join("\t".join(r) for r in rows) + "\n")

PY = "C:/Users/clyde/AppData/Local/Programs/Python/Python313/python.exe"
for cmd in ([PY, "D:/workbuddy_space/strata_ws/albus/w954/gen_ledger.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/audit_closure.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/progress.py"],
            [PY, "D:/workbuddy_space/strata_ws/tools/ledger_lint.py"]):
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()
    print("\n".join(out[:4]))
    print("---")
