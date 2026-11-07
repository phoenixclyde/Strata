#!/bin/bash
# ARM C: --mmap-experts（放弃 71.7 GiB anon arena，改用 page cache）
# 配置改动：args 追加 --mmap-experts；env 保持 dict 语义
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
cp -a "$P" "$P.bak_w975c"

python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]; c=json.load(open(p))
print("args type:",type(c["args"]).__name__,"len:",len(c["args"]))
a=[x for x in c["args"] if x!="--mmap-experts"]
a.append("--mmap-experts")
c["args"]=a
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("args now:",len(chk["args"]),"| has mmap:", "--mmap-experts" in chk["args"], "| env type:",type(chk["env"]).__name__)
PY

docker restart strata166-407 >/dev/null 2>&1 && echo restarted
for i in $(seq 1 60); do
  r=$(curl -s -m 3 localhost:8090/health || true)
  case "$r" in *'"loaded": true'*) echo "UP after ~$((i*5))s"; break;; esac
  sleep 5
done
docker ps --format '{{.Names}} {{.Status}}' | grep strata166
echo "--- 启动策略 ---"
grep -aE "loaded .* GiB at|expert arena|mmap|file tier" $LOG | tail -4
free -m | awk '/^Mem:/{printf "  MemAvailable=%d MiB Cached=%d MiB\n",$7,$6}'
echo "--- decode ---"
python3 - <<'PY'
import json,time,urllib.request
for i in range(3):
    txt="mmap probe %d. Explain in one paragraph why a cache hierarchy matters."%i
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
echo "--- 磁盘读取（这次应该有）---"
awk '{print "  sectors_read="$3}' /sys/block/nvme0n1/stat
