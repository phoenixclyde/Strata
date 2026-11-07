import io
import shutil

P = "albus/w1034/HANDOFF.md"
shutil.copyfile(P, P + ".bak_w1038")
s = io.open(P, encoding="utf-8").read()
pairs = [
    ("round=W1037 date=2026-11-07", "round=W1038 date=2026-11-07"),
]
for a, b in pairs:
    if a in s:
        s = s.replace(a, b, 1)
    else:
        print("WARN not found:", a[:50])
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("handoff snapshot -> W1038")
