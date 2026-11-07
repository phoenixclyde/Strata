#!/usr/bin/env python3
# 设置 STRATA_PREFILL_CPU_SHARE
import json, sys
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
v = sys.argv[1] if len(sys.argv) > 1 else "0"
d = json.load(open(p))
e = d.setdefault("env", {})
e["STRATA_PREFILL_CPU_SHARE"] = v
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("PREFILL_CPU_SHARE=%s env_n=%d" % (v, len(e)))
