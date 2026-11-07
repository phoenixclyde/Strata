# -*- coding: utf-8 -*-
"""AUDIT24 fix 1: repair PROGRESS rows R53/R54 whose evidence column was clobbered to '1'."""
import io

P = "D:/workbuddy_space/strata_ws/deploy/PROGRESS.tsv"
lines = io.open(P, encoding="utf-8").read().split("\n")
out = []
fixed = []
for ln in lines:
    f = ln.split("\t")
    if len(f) == 10 and f[1] in ("R53", "R54") and f[8].strip() == "1":
        # the evidence body was written into the ref column; split it back
        ref = f[9]
        # ref currently starts with "Wxxx;Wyyy 【...】<body>"
        head, _, body = ref.partition("】")
        head = head + "】"
        new_ref = head.replace("【", "").split("】")[0] if False else None
        # normalise: keep the W-list before the bracket as ref, the rest as note
        wlist = ref.split("】")[0]
        wlist = wlist.replace("【", ";").strip()
        note = body.strip()
        f[8] = note
        f[9] = wlist
        fixed.append((f[1], wlist[:30], len(note)))
        out.append("\t".join(f))
    else:
        out.append(ln)
io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out))
print("fixed", fixed)
