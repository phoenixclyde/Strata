#!/bin/bash
# W975: PLE 驻留 A/B —— arm A: 现状（auto->ram）；arm B: STRATA_PLE_AUTO_RAM=0
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log

measure(){
  local tag=$1 i r
  for i in $(seq 1 60); do
    r=$(curl -s -m 3 localhost:8090/health || true)
    case "$r" in *'"loaded": true'*) break;; esac
    sleep 5
  done
  echo "--- [$tag] 启动 ---"
  grep -a "loaded .* GiB at" $LOG | tail -1
  grep -aE "ple-io (ram|direct)|PLE .* (RAM|direct)" $LOG | tail -2
  free -m | awk '/^Mem:/{printf "  MemTotal=%d MiB  MemAvailable=%d MiB  Cached=%d MiB\n",$2,$7,$6}'
  echo "--- [$tag] decode ---"
  python3 - <<'PY'
import json,time,urllib.request
for i in range(3):
    txt="policy probe %d. Explain in one paragraph why a cache hierarchy matters."%i
    body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":128,"temperature":0.0}).encode()
    t0=time.time()
    r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
    u=r["usage"]; dt=time.time()-t0
    print("  decode%d  %d out  %.2f tok/s"%(i+1,u["completion_tokens"],u["completion_tokens"]/dt))
PY
  grep -aoE "decode timing: 4 windows.*" $LOG | tail -1 | cut -c1-110
  echo "--- [$tag] prefill 2.3K x2 ---"
  for w in alpha bravo; do
    python3 - "$w" <<'PY'
import json,sys,time,urllib.request
w=sys.argv[1]
txt=w+" "+"The quick brown fox jumps over the lazy dog. "*230
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":4,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
print("  %s wall=%.2fs"%(w,time.time()-t0))
PY
    grep -aoE "prompt [0-9]+ tokens = [0-9]+ reused \+ [0-9]+ read in [0-9]+ ms \([0-9.]+ tok/s\)" $LOG | tail -1
  done
}

echo "===== ARM A: 现状（PLE auto -> ram）====="
docker restart strata166-407 >/dev/null 2>&1
measure A

echo
echo "===== ARM B: STRATA_PLE_AUTO_RAM=0（direct）====="
python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]; c=json.load(open(p))
env=c["env"]
env=[e for e in env if not e.startswith("STRATA_PLE_AUTO_RAM=")]
env.append("STRATA_PLE_AUTO_RAM=0")
c["env"]=env
json.dump(c,open(p,"w"),indent=1)
print("  env count:",len(env))
PY
docker restart strata166-407 >/dev/null 2>&1
measure B
