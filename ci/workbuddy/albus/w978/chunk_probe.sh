#!/bin/bash
# P3: chunk 4096 vs 16384，看截距是否随 prompt-borrow 缩放
set -u
P=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
cp -a "$P" "$P.bak_w978"

set_chunk(){
  python3 - "$P" "$1" <<'PY'
import json,sys
p,val=sys.argv[1],sys.argv[2]
c=json.load(open(p))
a=c["args"]
if "--prefill" in a:
    a[a.index("--prefill")+1]=val
else:
    a += ["--prefill",val]
c["args"]=a
json.dump(c,open(p,"w"),indent=1)
chk=json.load(open(p))
print("  args:",len(chk["args"]),"prefill:",chk["args"][chk["args"].index("--prefill")+1],"env:",type(chk["env"]).__name__)
PY
}

probe(){
  for spec in "305:25" "1056:100" "2066:201"; do
    tok=${spec%%:*}; rep=${spec##*:}
    python3 - "$tok" "$rep" <<'PY'
import json,sys,time,urllib.request
tok,rep=sys.argv[1],int(sys.argv[2])
txt="chunk-"+tok+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300))
print("    wall=%.3fs prompt=%d"%(time.time()-t0, r["usage"]["prompt_tokens"]))
PY
  done
}

echo "=== A: --prefill 4096 ==="
set_chunk 4096
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 60); do r=$(curl -s -m 3 localhost:8090/health || true); case "$r" in *'"loaded": true'*) echo "  UP ~$((i*5))s"; break;; esac; sleep 5; done
grep -a "prompt path borrows" $LOG | tail -1
probe

echo
echo "=== B: 恢复 --prefill auto:16384 ==="
set_chunk auto:16384
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 60); do r=$(curl -s -m 3 localhost:8090/health || true); case "$r" in *'"loaded": true'*) echo "  UP ~$((i*5))s"; break;; esac; sleep 5; done
grep -a "prompt path borrows" $LOG | tail -1
probe
