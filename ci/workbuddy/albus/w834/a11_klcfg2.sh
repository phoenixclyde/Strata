#!/bin/bash
# W834b：数值债 5 项分项二分（每项各关一次），基线复用已在场的 E0
set -e
python3 - <<'PY'
import json
BASE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
OUT = "/home/albus/strata166/data/w834_%s.json"

ITEMS = {
    "rt0":   {"env": {"STRATA_ROUTE_TAIL_SKIP": "0"}},
    "kvfp16":{"args": {"--kv": "fp16"}},
    "pf0":   {"env": {"STRATA_HIP_PROMPT_F16": "0"}},
    "simt0": {"env": {"STRATA_SELECT_SIMT": "0"}},
    "hcq0":  {"env": {"STRATA_HC_Q8": "0"}},
}

for tag, spec in ITEMS.items():
    c = json.load(open(BASE))
    c["log"] = "/data/w834_%s.log" % tag
    env = dict(c.get("env") or {})
    env["STRATA_PREFILL_CPU_SHARE"] = "0"
    env["STRATA_LOGPOS"] = "/data/w834kl/%s.tsv" % tag.upper()
    env["STRATA_LOGPOS_TOPK"] = "64"
    for k, v in (spec.get("env") or {}).items():
        env[k] = v
    c["env"] = env
    a = list(c["args"])
    for k, v in (spec.get("args") or {}).items():
        if k in a:
            a[a.index(k) + 1] = v
        else:
            a += [k, v]
    c["args"] = a
    json.dump(c, open(OUT % tag, "w"), ensure_ascii=False, indent=1)
    print(tag, "env", len(env), "kv", a[a.index("--kv") + 1] if "--kv" in a else "?")
PY
