#!/usr/bin/env bash
# W941 / R61: collect PMC (VALUBusy) for a *production-shaped* prefill by launching the
# engine under rocprofv3 (launcher path), which W923's HSA_TOOLS_LIB injection never reached.
# Production container is stopped for the duration and restarted at the end.
set -u
H=/home/albus/strata166
OUT=$H/data/w941pmc
CFG=/data/strata-huihui-ud-iq4_xs.json
mkdir -p "$OUT"; rm -f "$OUT"/*.csv

echo "== stop prod =="
docker stop strata166-407 >/dev/null
echo "== start profiled engine =="
docker rm -f w941_pmc >/dev/null 2>&1
docker run -d --name w941_pmc \
  --device=/dev/kfd --device=/dev/dri \
  -v "$H/data":/data -v /models:/models:ro \
  -p 8090:8090 \
  strata-gfx906:0.2.10-101 \
  bash -lc "rocprofv3 --pmc VALUBusy -d /data/w941pmc -- python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
echo "== wait health =="
ok=0
for i in $(seq 1 300); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) ok=1; echo "loaded after $((i*4))s"; break;; esac
  sleep 4
done
if [ "$ok" != 1 ]; then
  echo "LOAD_FAILED"; docker logs --tail 40 w941_pmc 2>&1 | tail -40
  docker rm -f w941_pmc >/dev/null 2>&1; docker start strata166-407 >/dev/null; exit 1
fi

echo "== send 16K prompt (unique seed) =="
python3 - <<'PY'
import json, random, time, urllib.request
V="alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel lantern meadow nectar onyx prairie quartz ripple summit tundra umber vertex willow".split()
w=10240
rnd=random.Random(941777)
p=" ".join(rnd.choice(V) for _ in range(w))
body=json.dumps({"model":"probe","messages":[{"role":"user","content":p}],"max_tokens":1,"temperature":0,"stream":True}).encode()
req=urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"})
t0=time.time()
with urllib.request.urlopen(req,timeout=1800) as r:
    for line in r:
        s=line.decode().strip()
        if s.startswith("data:") and s[5:].strip()=="[DONE]": break
print("wall %.1f s" % (time.time()-t0))
PY

echo "== engine log =="
docker exec w941_pmc tail -40 /data/strata-huihui-ud-iq4_xs.log 2>/dev/null | grep -E "prompt .* tokens =" | tail -3

echo "== stop profiled, restore prod =="
docker stop w941_pmc >/dev/null; docker rm -f w941_pmc >/dev/null 2>&1
docker start strata166-407 >/dev/null
for i in $(seq 1 120); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
echo "== csv =="
ls -la "$OUT"
