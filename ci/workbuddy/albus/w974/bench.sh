#!/bin/bash
# 0.9.0 验收 bench：冷读 2.3K ×2 + 60K ×1
set -u
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
req(){ # $1 = 前缀词, $2 = 重复次数, $3 = 标签
python3 - "$1" "$2" <<'PY'
import json,sys,time,urllib.request
tag,rep=sys.argv[1],int(sys.argv[2])
txt=tag+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":8,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
print("  wall=%.2fs prompt=%s"%(time.time()-t0, r["usage"]["prompt_tokens"]))
PY
grep -oE "prompt [0-9]+ tokens = [0-9]+ reused \+ [0-9]+ read in [0-9]+ ms \([0-9.]+ tok/s\)" $LOG | tail -1
}
echo "== 2.3K #1 =="; req alpha 230
echo "== 2.3K #2 =="; req bravo 230
echo "== 60K ==";    req charlie 5900
echo "== 收尾 =="; curl -s -m 3 localhost:8090/health | head -c 60; echo
