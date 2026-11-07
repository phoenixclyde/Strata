#!/bin/bash
# 在 305-token 请求期间采样 GPU 占用与 CPU
set -u
rm -f /tmp/gpuuse.txt
( for i in $(seq 1 40); do
    u=$(rocm-smi --showuse 2>/dev/null | grep -oE "GPU use \(%\): [0-9]+" | grep -oE "[0-9]+$")
    echo "$(date +%s.%N) ${u:-NA}" >> /tmp/gpuuse.txt
    sleep 0.1
  done ) &
SAMPLER=$!
sleep 0.5
python3 - <<'PY'
import json,time,urllib.request
txt="use-probe "+"The quick brown fox jumps over the lazy dog. "*25
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=120))
print("  wall=%.3fs prompt=%d"%(time.time()-t0, r["usage"]["prompt_tokens"]))
PY
sleep 1
kill $SAMPLER 2>/dev/null
echo "== GPU use 采样（每 0.1s）=="
awk '{print $2}' /tmp/gpuuse.txt | tr '\n' ' '; echo
echo "== 非零占比 =="
awk '$2!="NA"{t++; if($2+0>5) b++} END{printf "  samples=%d  >5%%: %d (%.0f%%)\n", t, b, 100*b/t}' /tmp/gpuuse.txt
