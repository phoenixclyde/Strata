import sys, zlib
import msgpack

p = sys.argv[1]
raw = open(p, "rb").read()
print("raw size:", len(raw), "magic:", raw[:4])
for attempt in ("zlib", "raw"):
    try:
        buf = zlib.decompress(raw) if attempt == "zlib" else raw
    except Exception as e:
        print("  %s failed: %s" % (attempt, e))
        continue
    try:
        d = msgpack.unpackb(buf, raw=False, strict_map_key=False)
    except Exception as e:
        print("  %s unpack failed: %s" % (attempt, str(e)[:100]))
        continue
    print("  %s OK, type=%s" % (attempt, type(d).__name__))
    if isinstance(d, dict):
        print("  top keys:", list(d)[:12])
        sols = d.get("solutions", [])
        print("  n_solutions:", len(sols) if hasattr(sols, "__len__") else "?")
        if sols:
            s0 = sols[0] if isinstance(sols, list) else str(sols)[:80]
            print("  solution keys:", list(s0) if isinstance(s0, dict) else s0)
    break
