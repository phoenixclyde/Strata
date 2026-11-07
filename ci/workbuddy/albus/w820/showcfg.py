"""W820: 打印配置里与“换二进制”有关的字段（exe/cwd），并给出 A/B 用的派生配置。"""
import json
import sys

p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open(p, encoding="utf-8"))
for k in ("exe", "cwd", "engine", "family", "model"):
    print("%-8s = %r" % (k, d.get(k)))
print("keys:", sorted(k for k in d if k not in ("env", "args")))

if len(sys.argv) > 1:
    d["exe"] = sys.argv[1]
    out = sys.argv[2]
    json.dump(d, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote", out, "exe=", d["exe"], "args_n=", len(d["args"]))
