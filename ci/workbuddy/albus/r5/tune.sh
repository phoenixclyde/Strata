#!/bin/sh
# 用生产容器让出的显存跑 rocBLAS 解题表调优；结束后无条件重启生产。
set -u
TS=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/tune_rocblas_$TS.txt
TABLE=/home/albus/strata166/data/gfx906-rocblas-5.5.0.txt
CONT=strata166-407
STARTED=0

restore() {
  if [ "$STARTED" = "1" ]; then
    echo "=== restart prod $(date +%H:%M:%S) ===" >> "$OUT"
    docker start "$CONT" >/dev/null 2>&1
    for i in $(seq 1 240); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
      sleep 1
    done
    curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('after slots',e['expert_slots'],'vram',e['vram_free_mib'])" >> "$OUT" 2>&1
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
echo "vram_before=$(/opt/rocm/bin/rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 'Used' | tr -s ' ')" >> "$OUT"

trap 'restore' EXIT HUP INT TERM

docker stop -t 30 "$CONT" >> "$OUT" 2>&1 && echo "container stopped" >> "$OUT"
sleep 6
STARTED=1
echo "vram_free_now=$(/opt/rocm/bin/rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 'Used' | tr -s ' ')" >> "$OUT"

cd /home/albus/strata166/tmp/tune
./tune_rocblas --tokens 1024,2048,4096,8192 --min-gain 1.03 --tuning-out "$TABLE" >> "$OUT" 2>&1
echo "tuner rc=$?" >> "$OUT"
ls -l "$TABLE" >> "$OUT" 2>&1
head -6 "$TABLE" >> "$OUT" 2>&1
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
