# 清掉本轮新引入的禁用码位（U+2014），只动标点
import hashlib, io

FILES = [
    r"D:/workbuddy_space/strata_ws/deploy/W712_UPGRADE.md",
    r"D:/workbuddy_space/strata_ws/deploy/W712_PLAN.md",
    r"D:/workbuddy_space/strata_ws/deploy/configs/workbuddy-strata166.md",
    r"D:/workbuddy_space/strata_ws/deploy/scripts/_w712_b1_cacheevery.sh",
]
BAN = [0x21D2, 0x2192, 0x2014, 0x2013, 0x2026, 0x2265, 0x2264, 0x2260, 0x2212, 0x00D7]
SUB = [("\u2014\u2014", " - "), ("\u2014", "-"), ("\u2192", "->"), ("\u21d2", "=>"),
       ("\u2264", "<="), ("\u2265", ">="), ("\u2260", "!="), ("\u2212", "-"),
       ("\u00d7", "x"), ("\u2026", "...")]

for p in FILES:
    raw = open(p, "rb").read()
    t = raw.decode("utf-8")
    before = hashlib.md5(raw).hexdigest()
    n0 = sum(1 for c in t if ord(c) in BAN)
    if not n0:
        print("%-52s 已干净" % p.split("strata_ws/")[-1]); continue
    for a, b in SUB:
        t = t.replace(a, b)
    io.open(p, "w", encoding="utf-8", newline="\n").write(t)
    raw2 = open(p, "rb").read()
    n1 = sum(1 for c in raw2.decode("utf-8") if ord(c) in BAN)
    print("%-52s BAN %d -> %d  CR=%d  md5 %s -> %s" %
          (p.split("strata_ws/")[-1], n0, n1, raw2.count(b"\r"),
           before[:10], hashlib.md5(raw2).hexdigest()[:10]))
