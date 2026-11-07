import io

p = "albus/w1039/reply.md"
s = io.open(p, encoding="utf-8").read()
pairs = [
    ("StartedAt `2026-11-07T01:32:05Z`（= 09:32:05，第二窗口还原后的启动）",
     "StartedAt `2026-11-07T01:31:22Z`（= 09:31:22，第二窗口还原后的启动）"),
    ("used 33,495,166,976 / total 34,342,961,152 ⇒ **VRAM free 847,794,176 B（0.79 GiB）**",
     "used 33,495,207,936 / total 34,342,961,152 ⇒ **VRAM free 847,753,216 B（0.79 GiB）**"),
]
for a, b in pairs:
    if a in s:
        s = s.replace(a, b, 1)
        print("ok:", a[:40])
    else:
        print("MISS:", a[:40])
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
