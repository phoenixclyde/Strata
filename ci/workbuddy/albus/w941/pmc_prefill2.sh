#!/usr/bin/env bash
# W941 / R61 take 2: rocprofv3 must exec the *engine binary* itself (take 1 wrapped python3 and got no data).
# server.py launches `exe --serve ...`, so point config.exe at a wrapper that execs rocprofv3 -> engine.
set -u
H=/home/albus/strata166
OUT=$H/data/w941pmc
CFG=$H/data/strata-huihui-ud-iq4_xs.json
BAK=$CFG.bak_w941b
WRAP=$H/data/bin/pmc_wrap.sh

rm -rf "$OUT"; mkdir -p "$OUT"
cat > "$WRAP" <<'EOF'
#!/bin/bash
exec rocprofv3 --pmc VALUBusy -d /data/w941pmc -- /data/bin/strata-0.1.56 "$@"
EOF
chmod 755 "$WRAP"
cp "$CFG" "$BAK"
python3 - "$CFG" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p))
d['exe']='/data/bin/pmc_wrap.sh'
json.dump(d,open(p,'w'),indent=2)
PY
echo "exe -> $(python3 -c "import json;print(json.load(open('$CFG'))['exe'])")"

echo "== stop prod =="
docker stop strata166-407 >/dev/null
docker rm -f w941_pmc2 >/dev/null 2>&1
echo "== start wrapped =="
docker run -d --name w941_pmc2 --device=/dev/kfd --device=/dev/dri \
  -v "$H/data":/data -v /models:/models:ro -p 8090:8090 \
  strata-gfx906:0.2.10-101 \
  bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >/dev/null

ok=0
for i in $(seq 1 300); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) ok=1; echo "loaded after $((i*4))s"; break;; esac
  sleep 4
done
if [ "$ok" != 1 ]; then
  echo LOAD_FAILED; docker logs --tail 30 w941_pmc2 2>&1 | tail -30
  docker rm -f w941_pmc2 >/dev/null 2>&1
  cp "$BAK" "$CFG"; docker start strata166-407 >/dev/null; exit 1
fi

echo "== 16K prompt =="
python3 - <<'PY'
import json, random, time, urllib.request
V="alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec romeo sierra tango uniform victor whiskey xray yankee zulu amber basalt cobalt dune ember fjord granite harbor inlet jetty kernel lantern meadow nectar onyx prairie quartz ripple summit tundra umber vertex willow".split()
rnd=random.Random(942777); p=" ".join(rnd.choice(V) for _ in range(10240))
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
docker exec w941_pmc2 tail -30 /data/strata-huihui-ud-iq4_xs.log 2>/dev/null | grep -E "prompt .* tokens =" | tail -2
echo "== csv so far =="
find "$OUT" -type f | head

echo "== stop + restore =="
docker stop w941_pmc2 >/dev/null; docker rm -f w941_pmc2 >/dev/null 2>&1
cp "$BAK" "$CFG"
rm -f "$WRAP"
docker start strata166-407 >/dev/null
for i in $(seq 1 120); do
  r=$(curl -s -m 2 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "prod back after $((i*4))s"; break;; esac
  sleep 4
done
find "$OUT" -type f | head
