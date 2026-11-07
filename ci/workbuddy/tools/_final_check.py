# -*- coding: utf-8 -*-
"""收尾核验：新工作区清单 + 新写件禁用码位/CR 自检。"""
import hashlib
import io
import os

WS = r"D:/workbuddy_space/strata_ws"
BAN = {
    0x21D2: "U+21D2", 0x2192: "U+2192", 0x2014: "U+2014", 0x2013: "U+2013",
    0x2026: "U+2026", 0x2265: "U+2265", 0x2264: "U+2264", 0x2260: "U+2260",
    0x2212: "U+2212", 0x00D7: "U+00D7",
}

MINE = [
    "PROJECT.md",
    "HANDOVER.md",
    "MAP_OLD_TO_NEW.md",
    ".workbuddy/memory/MEMORY.md",
    "tools/_verify_copy.py",
    "tools/_verify_copy_out.md",
    "tools/_verify_copy_out.PREDELETE.md",
    "tools/_w710_append.py",
    "tools/_stub_routek_mem.py",
]


def scan(p):
    b = io.open(p, "rb").read()
    cr = b.count(b"\r")
    t = b.decode("utf-8", "replace")
    hits = sorted({BAN[ord(c)] for c in t if ord(c) in BAN})
    return len(b), cr, hits, hashlib.md5(b).hexdigest()


print("=== 新写件自检（禁用码位 / CR / 指纹） ===")
for rel in MINE:
    p = os.path.join(WS, rel.replace("/", os.sep))
    if not os.path.isfile(p):
        print("  [缺失] %s" % rel)
        continue
    n, cr, hits, m = scan(p)
    flag = "OK " if (not cr and not hits) else "!! "
    print("  %s%-42s %7d B  md5=%s  CR=%d  BAN=%s" % (flag, rel, n, m[:12], cr, (",".join(hits) if hits else "clean")))

print()
print("=== 记忆件（历史件，单独报） ===")
for rel in [".workbuddy/memory/2026-10-08.md", ".workbuddy/memory/2026-10-07.md"]:
    p = os.path.join(WS, rel.replace("/", os.sep))
    n, cr, hits, m = scan(p)
    print("  %-42s %7d B  md5=%s  CR=%d  BAN=%s" % (rel, n, m[:12], cr, (",".join(hits) if hits else "clean")))

print()
print("=== 新工作区顶层 ===")
for name in sorted(os.listdir(WS)):
    p = os.path.join(WS, name)
    if os.path.isdir(p):
        c = sum(len(f) for _r, _d, f in os.walk(p))
        print("  [DIR ] %-22s %d files" % (name, c))
    else:
        print("  [FILE] %-22s %d B" % (name, os.path.getsize(p)))
