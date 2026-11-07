#!/bin/bash
# 回滚 ARM C：移除 --mmap-experts，恢复 resident arena
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]; c=json.load(open(p))
c["args"]=[x for x in c["args"] if x!="--mmap-experts"]
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("args:",len(chk["args"]),"env type:",type(chk["env"]).__name__,"env:",len(chk["env"]),"exe:",chk["exe"])
PY
docker restart strata166-407 >/dev/null 2>&1 && echo restarted
for i in $(seq 1 60); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after ~$((i*5))s"; break;; esac
  sleep 5
done
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
grep -aE "loaded .* GiB at|expert arena read through" $LOG | tail -2
free -m | awk '/^Mem:/{printf "  MemAvailable=%d MiB Cached=%d MiB\n",$7,$6}'
echo "--- 复核 decode ---"
python3 - <<'PY'
import json,time,urllib.request
for i in range(2):
    txt="revert probe %d. Explain in one paragraph why a cache hierarchy matters."%i
    body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":128,"temperature":0.0}).encode()
    t0=time.time()
    r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
    u=r["usage"]; dt=time.time()-t0
    print("  decode%d %.2f tok/s"%(i+1,u["completion_tokens"]/dt))
PY
echo "--- 复核 prefill 2.3K ---"
python3 - <<'PY'
import json,time,urllib.request
txt="revert "+"The quick brown fox jumps over the lazy dog. "*230
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":4,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
print("  wall=%.2fs"%(time.time()-t0))
PY
grep -aoE "prompt [0-9]+ tokens = .* tok/s\)" $LOG | tail -1
