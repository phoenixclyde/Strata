import io, shutil

P = "albus/w1034/HANDOFF.md"
shutil.copyfile(P, P + ".bak_w1037")
s = io.open(P, encoding="utf-8").read()
pairs = [
    ("round=W1036 date=2026-11-07", "round=W1037 date=2026-11-07"),
    ("branch=6501c28f tag=mi50-0.2.11-r33-14", "branch=e181bda5 tag=mi50-0.2.11-r33-14"),
    ("| 主线 | `gfx906/mi50` @ `6501c28f` · tag `mi50-0.2.11-r33-14` · 领先 78 / 落后 0 · **脏 0 行**（在 166 上） |",
     "| 主线 | `gfx906/mi50` @ `e181bda5`（`mi50-0.2.11-r33-14-2-ge181bda5`）· 领先 80 / 落后 0 · **脏 0 行**（在 166 上）；实验分支 `gfx906/port-all` @ `8b44f3d1`（领先 2） |"),
]
for a, b in pairs:
    if a in s:
        s = s.replace(a, b, 1)
    else:
        print("WARN not found:", a[:50])
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("handoff snapshot updated")
