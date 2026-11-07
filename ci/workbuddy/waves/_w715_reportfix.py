# 修正 W715 报告里的禁用码位（项目铁律：交付件禁用码位须为 0，CR=0）
import io, os

OUT = r"D:/workbuddy_space/strata_ws/deploy/W715_HUIHUI_SWITCH.md"
MAP = {
    0x21D2: "=>", 0x2192: "->", 0x2014: "--", 0x2013: "-", 0x2026: "...",
    0x2265: ">=", 0x2264: "<=", 0x2260: "!=", 0x2212: "-", 0x00D7: "x",
}
t = io.open(OUT, encoding="utf-8").read()
found = {}
for i, ch in enumerate(t):
    if ord(ch) in MAP:
        found.setdefault(hex(ord(ch)), []).append(i)
print("修正前发现的禁用码位:", {k: len(v) for k, v in found.items()})
for k, v in found.items():
    i = v[0]
    print("  例: ... %r ..." % t[max(0, i - 40):i + 40])

out = "".join(MAP.get(ord(c), c) for c in t)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(out)
back = io.open(OUT, encoding="utf-8").read()
bad = [hex(ord(c)) for c in back if ord(c) in MAP]
print("修正后: 禁用码位=%d  CR=%d  %d B" % (len(bad), back.count("\r"), os.path.getsize(OUT)))
assert not bad and back.count("\r") == 0, "仍有问题"
print("OK")
