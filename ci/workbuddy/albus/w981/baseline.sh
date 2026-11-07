#!/bin/bash
# 当前生产基线：与昨天同条件（冷读、唯一前缀、同长度）
set -u
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
probe(){
  local tag=$1 rep=$2
  python3 - "$tag" "$rep" <<'PY'
import json,sys,time,secrets,urllib.request
tag,rep=sys.argv[1],int(sys.argv[2])
txt=tag+" "+secrets.token_hex(3)+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":4,"temperature":0.0}).encode()
t=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=900))
print("   wall=%.2fs prompt=%d"%(time.time()-t,r["usage"]["prompt_tokens"]))
PY
  grep -aoE "prompt [0-9]+ tokens = .* tok/s\)" $LOG | tail -1
}

echo "== 2.35K #1 =="; probe base1 230
echo "== 2.35K #2 =="; probe base2 230
echo "== 59K  #1 =="; probe base3 5900
echo "== 尾状态 =="; curl -s -m 3 localhost:8090/health | head -c 60; echo
