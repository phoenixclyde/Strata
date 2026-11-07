#!/bin/bash
# W833 P0-c：数值债三臂配置（+ 一个基线复本作噪声地板）
set -e
mkdir -p /home/albus/strata166/data/w833kl
python3 - <<'PY'
import json
BASE = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
OUT = "/home/albus/strata166/data/w833_%s.json"

def mk(tag, tsv, extra):
    c = json.load(open(BASE))
    c["log"] = "/data/w833_%s.log" % tag
    env = dict(c.get("env") or {})
    env["STRATA_PREFILL_CPU_SHARE"] = "0"      # 硬前提：否则底噪(0.025)与效应同量级
    env["STRATA_LOGPOS"] = tsv
    env["STRATA_LOGPOS_TOPK"] = "64"
    for k, v in extra.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    c["env"] = env
    json.dump(c, open(OUT % tag, "w"), ensure_ascii=False, indent=1)
    print(tag, "env", len(env), "extra", extra)

mk("kle0",   "/data/w833kl/E0.tsv", {})
mk("kle0b",  "/data/w833kl/E0b.tsv", {})
mk("klemmq", "/data/w833kl/EM.tsv", {"STRATA_MMQ_KQ": "0"})
mk("klegdn", "/data/w833kl/EG.tsv", {"STRATA_GDN_HEAD": "0"})
PY
ls -la /home/albus/strata166/data/w833_kle*.json
