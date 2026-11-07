import zlib, sys
import msgpack
p = sys.argv[1]
raw = open(p, "rb").read()
try:
    raw = zlib.decompress(raw)
except Exception:
    pass
d = msgpack.unpackb(raw, raw=False, strict_map_key=False)
print("top keys:", list(d) if isinstance(d, dict) else type(d))
if isinstance(d, dict):
    sols = d.get("solutions", [])
    print("n_solutions:", len(sols))
    if sols:
        print("solution keys:", list(sols[0]))
        print("hardwarePredicate present:", "hardwarePredicate" in sols[0])
    rows = d.get("library", {}).get("rows", []) if isinstance(d.get("library"), dict) else []
    for i, r in enumerate(rows):
        print(" row", i, "keys:", list(r))
