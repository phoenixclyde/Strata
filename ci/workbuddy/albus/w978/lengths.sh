#!/bin/bash
# W978 六长度档冷读基线（新盘 + PLE mmap + v0.9.0）
set -u
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
for spec in "2K:200" "8K:790" "16K:1570" "32K:3140" "64K:6280" "130K:12750"; do
  tag=${spec%%:*}; rep=${spec##*:}
  echo "=== $tag (rep=$rep) ==="
  python3 - "$tag" "$rep" <<'PY'
import json,sys,time,urllib.request
tag,rep=sys.argv[1],int(sys.argv[2])
txt=tag+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":4,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=900))
u=r["usage"]
print("  wall=%.2fs prompt=%d out=%d"%(time.time()-t0,u["prompt_tokens"],u["completion_tokens"]))
PY
  grep -aoE "prompt [0-9]+ tokens = .* tok/s\)" $LOG | tail -1
done
echo "=== done ==="
