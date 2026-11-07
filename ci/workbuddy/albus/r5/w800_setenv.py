#!/usr/bin/env python3
# 设置/删除 STRATA_PREFILL_STREAM_MIN（空字符串=删除）
import json, sys, os
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
v = sys.argv[1] if len(sys.argv) > 1 else ""
d = json.load(open(p))
e = d.setdefault("env", {})
if v == "":
    e.pop("STRATA_PREFILL_STREAM_MIN", None)
else:
    e["STRATA_PREFILL_STREAM_MIN"] = v
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("STREAM_MIN=%s env_n=%d" % (v or "ABSENT", len(e)))
