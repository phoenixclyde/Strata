#!/bin/bash
# Bounded experiment: run the S1 (tile_spec) engine, find out HOW it fails, always roll back.
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
restore() {
  echo "=== restore: rollback to 001"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -3
  curl -s -m 5 localhost:8090/health | head -c 60; echo
}
trap restore EXIT

echo "=== deploy S1 (strata-0.1.57-003)"
bash ci/deploy.sh --src /home/albus/strata166/build-lcpp --exe strata-0.1.57-003 --apply 2>&1 | tail -6
for i in $(seq 1 12); do h=$(curl -s -m 3 localhost:8090/health || true); case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac; sleep 10; done

probe() {
  python3 - "$1" "$2" <<'PY'
import json,sys,time,urllib.request
n=int(sys.argv[1]); label=sys.argv[2]
words="the quick brown fox jumps over lazy dog while seven wizards vex my cryptic jynx quiet zebra alpha bravo charlie delta".split()
import random; random.seed(11)
p=" ".join(random.choice(words) for _ in range(n))
body=json.dumps({"model":"x","messages":[{"role":"user","content":p}],"max_tokens":4,"temperature":0.0}).encode()
r=urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"})
t0=time.perf_counter()
try:
    d=json.loads(urllib.request.urlopen(r,timeout=90).read())
    print("%-8s words=%-4d ptok=%-5s %.2fs OK" % (label,n,d.get("usage",{}).get("prompt_tokens"),time.perf_counter()-t0))
except Exception as e:
    print("%-8s words=%-4d FAILED after %.1fs: %s" % (label,n,time.perf_counter()-t0,type(e).__name__+": "+str(e)[:90]))
PY
}
echo "=== probes"
probe 8   small
probe 75  at75
probe 400 big
echo "=== engine state after probes:"
curl -s -m 5 localhost:8090/health | head -c 80; echo
docker inspect -f "restarts={{.RestartCount}} status={{.State.Status}}" strata166-407
echo "=== last log lines:"
docker logs --tail 22 strata166-407 2>&1 | tail -22 | cut -c1-170
