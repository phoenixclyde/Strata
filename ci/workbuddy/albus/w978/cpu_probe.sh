#!/bin/bash
# 量 305 / 2066 token 请求的 CPU 时间与 GPU 占用
set -u
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
echo "engine host pid=$PID"

run(){
  local tag=$1 rep=$2
  local c0 c1 t0 t1
  c0=$(sudo awk '{print $14+$15}' /proc/$PID/stat)
  rm -f /tmp/g.txt
  ( for i in $(seq 1 60); do
      u=$(rocm-smi --showuse 2>/dev/null | grep -oE "GPU use \(%\): [0-9]+" | grep -oE "[0-9]+$")
      echo "${u:-NA}" >> /tmp/g.txt; sleep 0.05
    done ) &
  local S=$!
  t0=$(date +%s.%N)
  python3 - "$tag" "$rep" <<'PY'
import json,sys,time,urllib.request
tag,rep=sys.argv[1],int(sys.argv[2])
txt=tag+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300))
print("   wall=%.3fs prompt=%d"%(time.time()-t,r["usage"]["prompt_tokens"]))
PY
  t1=$(date +%s.%N)
  sleep 0.4; kill $S 2>/dev/null
  c1=$(sudo awk '{print $14+$15}' /proc/$PID/stat)
  local busy
  busy=$(awk '$1!="NA"{t++; if($1+0>5) b++} END{printf "%d/%d", b+0, t+0}' /tmp/g.txt)
  printf "   cpu=%.2fs  wall=%.2fs  gpu_busy_samples=%s\n" \
    "$(awk -v a=$c0 -v b=$c1 'BEGIN{print (b-a)/100}')" \
    "$(awk -v a=$t0 -v b=$t1 'BEGIN{print b-a}')" "$busy"
}

echo "=== 305 tok ==="; run cpu305 25
echo "=== 2066 tok ==="; run cpu2066 201
echo "=== 305 tok (repeat) ==="; run cpu305b 25
