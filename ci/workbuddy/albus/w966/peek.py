import json
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
c = json.load(open(p))
print("keys:", list(c.keys()))
for k in ("exe", "bin", "engine", "port", "host"):
    if k in c:
        print(k, "=", c[k])
args = c.get("args") or c.get("argv") or []
print("n_args:", len(args))
print("args head:", " ".join(map(str, args))[:300])
