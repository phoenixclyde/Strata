#!/bin/bash
# 小长度扫描：拟合 t = a + n/b，定位固定成本
set -u
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
for spec in "128:13" "256:25" "512:50" "1024:100" "2048:201" "4096:401"; do
  tag=${spec%%:*}; rep=${spec##*:}
  python3 - "$tag" "$rep" <<'PY'
import json,sys,time,urllib.request
tag,rep=sys.argv[1],int(sys.argv[2])
txt=tag+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300))
print("  wall=%.3fs prompt=%d"%(time.time()-t0, r["usage"]["prompt_tokens"]))
PY
  grep -aoE "prompt [0-9]+ tokens = .* read in [0-9]+ ms" $LOG | tail -1
done
