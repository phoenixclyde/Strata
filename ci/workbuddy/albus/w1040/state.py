#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1040: read-only production cross-section + candidate facts, zero downtime."""
import io, os, sys, json, re
sys.path.insert(0, r"D:/workbuddy_space/strata_ws/deploy/params")
import _sshutil

S = r'''
set +e
C=strata166-407
echo "== container =="
docker inspect -f '{{.Id}}|{{.Config.Image}}|{{.State.Status}}|{{.RestartCount}}|{{.State.StartedAt}}' $C
docker inspect -f '{{.HostConfig.Ulimits}}' $C
echo "== running engine =="
pgrep -a -x strata-host
RP=$(pgrep -a -x strata-host | awk '{print $2}')
md5sum "$RP"; stat -c%s "$RP"
echo "== config =="
md5sum /home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
python3 - <<'PY'
import json,io
d=json.load(io.open("/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json",encoding="utf-8-sig"))
print("exe=",d.get("exe"),"| args=",len(d.get("args",[])),"| env=",len(d.get("env",{})))
print("kv-grow in args:", "--kv-grow" in d.get("args",[]), "| STRATA_KV_GROW=", (d.get("env") or {}).get("STRATA_KV_GROW"))
PY
echo "== health =="
curl -s -m 8 localhost:8090/health
echo
echo "== vram =="
rocm-smi --showmeminfo vram 2>/dev/null | grep -iE "used|total" | head -4
echo "== slots / elastic =="
grep -a "expert cache .* slots" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2
grep -a "elastic K/V" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2
grep -a -- "--kv-grow is off" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -1
echo "== bin dir =="
ls -1 /home/albus/strata166/data/bin | grep -c 'strata-0.1'
md5sum /home/albus/strata166/data/bin/strata-0.1.57-kvg /home/albus/strata166/data/bin/strata-0.1.57-b12180 2>&1
stat -c'%n %s' /home/albus/strata166/data/bin/strata-0.1.57-kvg 2>&1
echo "== numeric gate assets =="
ls -la /home/albus/strata166/tmp/w1041/qq_k8v4.py /home/albus/strata166/pr/k10/data/quant_quality/v1/set.ids.json 2>&1 | head -5
python3 -c "import json;d=json.load(open('/home/albus/strata166/pr/k10/data/quant_quality/v1/set.ids.json'));print(type(d).__name__, len(d));print(json.dumps(d)[:200])" 2>&1
echo "== arm json =="
ls -la /home/albus/strata166/tmp/w1039/arm_kvg*.json 2>&1
echo "== uptime / load =="
uptime
'''

rc, out, err = _sshutil.run_remote(S, timeout=120)
print("rc=", rc)
print(out)
if err.strip():
    print("STDERR:", err[-2000:])
