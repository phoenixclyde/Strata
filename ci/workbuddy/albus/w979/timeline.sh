#!/bin/bash
# 时间分辨：每 100ms 记录 GPU 占用 + 进程 CPU jiffies
set -u
PID=$(pgrep -f 'strata-0.1.56-090' | head -1)
OUT=/tmp/tl.txt
rm -f $OUT
( for i in $(seq 1 80); do
    u=$(rocm-smi --showuse 2>/dev/null | grep -oE "GPU use \(%\): [0-9]+" | grep -oE "[0-9]+$")
    c=$(sudo awk '{print $14+$15}' /proc/$PID/stat 2>/dev/null)
    echo "$(date +%s.%N) ${u:-NA} ${c:-0}" >> $OUT
    sleep 0.1
  done ) &
S=$!
sleep 0.3
python3 - <<'PY' > /tmp/req.txt
import json,time,urllib.request
txt="timeline "+"The quick brown fox jumps over the lazy dog. "*25
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":2,"temperature":0.0}).encode()
t=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=300))
print("%.3f %.3f %d"%(t,time.time()-t,r["usage"]["prompt_tokens"]))
PY
sleep 0.6; kill $S 2>/dev/null
cat /tmp/req.txt
echo "   t_rel  gpu%  cpu_delta_s"
python3 - <<'PY'
rows=[l.split() for l in open('/tmp/tl.txt') if len(l.split())==3]
t0=float(open('/tmp/req.txt').read().split()[0])
prev=None
for ts,g,c in rows:
    ts=float(ts); c=int(c)
    d=0 if prev is None else (c-prev)/100.0
    prev=c
    rel=ts-t0
    if -0.4 < rel < 3.2:
        print("  %6.2f  %4s  %5.2f"%(rel,g,d))
PY
