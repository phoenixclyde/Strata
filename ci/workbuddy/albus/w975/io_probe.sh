#!/bin/bash
# 量一次冷读请求的磁盘/CPU/时间分布
# usage: io_probe.sh <tag> <repeat>
set -u
TAG=$1; REP=$2
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
PID=$(docker exec strata166-407 ps -eo pid,cmd | grep '[s]trata-0.1.56-090' | awk '{print $1}' | head -1)

rd(){ awk '{print $3}' /sys/block/nvme0n1/stat; }   # sectors read
tm(){ awk '{print $14+$15}' /proc/$PID/stat 2>/dev/null; }  # utime+stime (ticks)

R0=$(rd); T0=$(tm)
python3 - "$TAG" "$REP" <<'PY'
import json,sys,time,urllib.request
tag,rep=sys.argv[1],int(sys.argv[2])
txt=tag+" "+"The quick brown fox jumps over the lazy dog. "*rep
body=json.dumps({"model":"x","messages":[{"role":"user","content":txt}],"max_tokens":8,"temperature":0.0}).encode()
t0=time.time()
r=json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",data=body,headers={"Content-Type":"application/json"}),timeout=600))
print("  wall=%.2fs prompt=%s"%(time.time()-t0, r["usage"]["prompt_tokens"]))
PY
R1=$(rd); T1=$(tm)
SECT=$((R1-R0)); TICKS=$((T1-T0))
printf '  disk_read=%d MiB  cpu=%.2fs\n' $((SECT/2048)) $(awk -v t=$TICKS 'BEGIN{print t/100}')
grep -oE "prompt [0-9]+ tokens = [0-9]+ reused \+ [0-9]+ read in [0-9]+ ms \([0-9.]+ tok/s\)" $LOG | tail -1
