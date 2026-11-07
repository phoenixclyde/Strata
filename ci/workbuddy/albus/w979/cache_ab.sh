#!/bin/bash
# P4: 关掉 conversation-cache 与 prompt-cache-every，看截距
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
cp -a "$P" "$P.bak_w979"

probe(){
  for spec in "25:305" "201:2066"; do
    rep=${spec%%:*}; tok=${spec##*:}
    python3 - "$tok" "$rep" <<'PY'
import json,sys,time,urllib.request
tok,rep=sys.argv[1],int(sys.argv[2])
txt="pc-"+tok+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300))
print("    wall=%.3fs prompt=%d"%(time.time()-t,r["usage"]["prompt_tokens"]))
PY
  done
}

echo "=== A: 关掉 conversation-cache-mib 与 prompt-cache-every ==="
python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]; c=json.load(open(p)); a=c["args"]
def setv(flag,val):
    if flag in a: a[a.index(flag)+1]=val
    else: a += [flag,val]
setv("--conversation-cache-mib","0")
setv("--prompt-cache-every","0")
c["args"]=a
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("  args:",len(chk["args"]),"cc:",chk["args"][chk["args"].index("--conversation-cache-mib")+1],
      "pce:",chk["args"][chk["args"].index("--prompt-cache-every")+1],"env:",type(chk["env"]).__name__)
PY
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 60); do r=$(curl -s -m 3 localhost:8090/health || true); case "$r" in *'"loaded": true'*) echo "  UP ~$((i*5))s"; break;; esac; sleep 5; done
probe

echo
echo "=== B: 恢复 4096 / 8192 ==="
python3 - "$P" <<'PY'
import json,sys
p=sys.argv[1]; c=json.load(open(p)); a=c["args"]
a[a.index("--conversation-cache-mib")+1]="4096"
a[a.index("--prompt-cache-every")+1]="8192"
c["args"]=a
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("  args:",len(chk["args"]),"cc:",chk["args"][chk["args"].index("--conversation-cache-mib")+1],
      "pce:",chk["args"][chk["args"].index("--prompt-cache-every")+1])
PY
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 60); do r=$(curl -s -m 3 localhost:8090/health || true); case "$r" in *'"loaded": true'*) echo "  UP ~$((i*5))s"; break;; esac; sleep 5; done
probe
