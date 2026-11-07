#!/usr/bin/env python3
# 设置 STRATA_ROUTE_TAIL_SKIP（空=删除）
import json, sys
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
v = sys.argv[1] if len(sys.argv) > 1 else ""
d = json.load(open(p))
e = d.setdefault("env", {})
if v == "":
    e.pop("STRATA_ROUTE_TAIL_SKIP", None)
else:
    e["STRATA_ROUTE_TAIL_SKIP"] = v
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("ROUTE_TAIL_SKIP=%s env_n=%d" % (v or "ABSENT", len(e)))
