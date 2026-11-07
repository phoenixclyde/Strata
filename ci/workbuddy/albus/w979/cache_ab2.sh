#!/bin/bash
# P4-c 重做：conversation-cache / prompt-cache-every 关 vs 开，各 3 次采样
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
cp -a "$P" "$P.bak_w979b"

apply(){
  python3 - "$P" "$1" "$2" <<'PY'
import json,sys
p,cc,pce=sys.argv[1],sys.argv[2],sys.argv[3]
c=json.load(open(p)); a=list(c["args"])
def setv(flag,val):
    if flag in a: a[a.index(flag)+1]=val
    else: a.extend([flag,val])
setv("--conversation-cache-mib",cc)
setv("--prompt-cache-every",pce)
c["args"]=a
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("  args:",len(chk["args"]),"cc:",chk["args"][chk["args"].index("--conversation-cache-mib")+1],
      "pce:",chk["args"][chk["args"].index("--prompt-cache-every")+1],
      "prefill:",chk["args"][chk["args"].index("--prefill")+1],"env:",type(chk["env"]).__name__)
PY
}

restart_wait(){
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 60); do r=$(curl -s -m 3 localhost:8090/health || true); case "$r" in *'"loaded": true'*) return 0;; esac; sleep 5; done
  return 1
}

samples(){
  local i
  # warm-up（丢弃）
  python3 - <<'PY'
import json,urllib.request
body=json.dumps({"model":"x","messages":[{"role":"user","content":"warmup discard"}],"max_tokens":2,"temperature":0.0}).encode()
urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=120).read()
PY
  for i in 1 2 3; do
    python3 - "$i" <<'PY'
import json,sys,time,urllib.request
i=sys.argv[1]
txt="s"+i+" "+"The quick brown fox jumps over the lazy dog. "*25
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300))
print("    s%s wall=%.3fs prompt=%d"%(i,time.time()-t,r["usage"]["prompt_tokens"]))
PY
  done
}

echo "=== A: cc=0 pce=0 ==="
apply 0 0
restart_wait && echo "  UP"
samples

echo
echo "=== B: cc=4096 pce=8192（恢复现役）==="
apply 4096 8192
restart_wait && echo "  UP"
samples
