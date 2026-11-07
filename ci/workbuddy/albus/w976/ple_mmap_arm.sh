#!/bin/bash
# ARM D: --ple-io mmap（与 ram 同一访问路径，只是不 mlock）
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
cp -a "$P" "$P.bak_w976"

python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]; c=json.load(open(p))
a=[x for x in c["args"]]
# 去掉已有的 --ple-io 及其值
out=[];skip=False
for x in a:
    if skip: skip=False; continue
    if x=="--ple-io": skip=True; continue
    out.append(x)
out += ["--ple-io","mmap"]
c["args"]=out
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("args:",len(chk["args"]),"| ple-io:",chk["args"][chk["args"].index("--ple-io")+1] if "--ple-io" in chk["args"] else None,
      "| env type:",type(chk["env"]).__name__)
PY

docker restart strata166-407 >/dev/null 2>&1 && echo restarted
for i in $(seq 1 60); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after ~$((i*5))s"; break;; esac
  sleep 5
done
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
echo "--- PLE 策略确认 ---"
grep -aE "PLE table|ple-io" $LOG | tail -3
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
sudo awk '/^(Rss|Anonymous|Locked):/{printf "  %-12s %7.2f GiB\n",$1,$2/1048576}' /proc/$PID/smaps_rollup
free -m | awk '/^Mem:/{printf "  MemAvailable=%d MiB Cached=%d MiB\n",$7,$6}'
echo "--- decode ---"
python3 - <<'PY'
import json,time,urllib.request
for i in range(3):
    txt="mmap-ple probe %d. Explain in one paragraph why a cache hierarchy matters."%i
    body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":128,"temperature":0.0}).encode()
    t0=time.time()
    r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
    u=r["usage"]; dt=time.time()-t0
    print("  decode%d %d out %.2f tok/s"%(i+1,u["completion_tokens"],u["completion_tokens"]/dt))
PY
echo "--- prefill 2.3K x2 ---"
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
  grep -aoE "prompt [0-9]+ tokens = .* tok/s\)" $LOG | tail -1
done
