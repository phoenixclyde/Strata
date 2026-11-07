import sys, zlib
import msgpack

for p in sys.argv[1:]:
    raw = open(p, "rb").read()
    try:
        buf = zlib.decompress(raw)
    except Exception:
        buf = raw
    try:
        d = msgpack.unpackb(buf, raw=False, strict_map_key=False)
    except Exception as e:
        print(p, "UNPACK FAIL", str(e)[:80])
        continue
    print("=== %s  bytes=%d/%d" % (p.split("/")[-1], len(raw), len(buf)))
    if isinstance(d, dict):
        print("  top keys:", list(d))
        sols = d.get("solutions", [])
        print("  n_solutions:", len(sols))
        if sols:
            s = sols[0]
            print("  sol keys:", list(s))
            print("  hardwarePredicate present:", "hardwarePredicate" in s)
            print("  index:", s.get("index"), " name:", str(s.get("name"))[:50])
