#!/bin/bash
# 造 W832 实验配置：与生产逐字段相同，只改 log + 加 STRATA_DECODE_TIMING
set -e
python3 - <<'PY'
import json, copy, hashlib
src = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
dst = "/home/albus/strata166/data/w832_tune.json"
c = json.load(open(src))
d = copy.deepcopy(c)
d["log"] = "/data/w832_tune.log"
env = dict(d.get("env") or {})
env["STRATA_DECODE_TIMING"] = "1"
d["env"] = env
json.dump(d, open(dst, "w"), indent=2)
print("args same :", d["args"] == c["args"], "n=", len(d["args"]))
print("env  before/after:", len(c.get("env") or {}), "->", len(env))
print("exe:", d["exe"])
print("added env:", sorted(set(env) - set((c.get('env') or {}))))
print("log:", d["log"])
PY
echo
echo "=== 生产配置指纹（未动） ==="
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
