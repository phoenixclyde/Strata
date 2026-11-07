#!/bin/sh
# W793b：0.2.4p3 已就位，只跑三臂（A 基 / B +rocBLAS表 / C +SIMT=1），交错 A B C A B C。
# 每臂 docker restart（改 env 必须重启，docker start 对运行中的容器是空操作 —— 上一轮就栽在这）。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w793b_ab_$TS.txt
BAK=$CFG.bak_w793b_$TS
CONT=strata166-407
TABLE=/data/gfx906-rocblas-5.5.0.txt
OKFLAG=/tmp/w793b_done

rm -f "$OKFLAG"

set_env() {
  python3 - "$CFG" "$1" "$TABLE" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm, table = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(cfg))
e = {k: v for k, v in d.get('env', {}).items()
     if k not in ('STRATA_PREFILL_TIMING', 'STRATA_ROCBLAS_TUNING', 'STRATA_SELECT_SIMT', 'STRATA_ROCBLAS_VERBOSE')}
e['STRATA_PREFILL_TIMING'] = '1'
if arm == 'B':
    e['STRATA_ROCBLAS_TUNING'] = table
if arm == 'C':
    e['STRATA_SELECT_SIMT'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('arm', arm, 'env', sorted(e.items()))
PY
}

restart_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 240); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 8
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restart $(date +%H:%M:%S) ===" >> "$OUT"
    restart_up
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK" >> "$OUT"
echo "image=$(docker inspect -f '{{.Config.Image}}' $CONT)" >> "$OUT"
echo "governor=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c | tr '\n' ' ')" >> "$OUT"

trap 'keepup' EXIT HUP INT TERM

for arm in A B C A B C; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$arm"
  restart_up
  prev=$(grep -a -c "strata prefill timing" "$LOG")
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  now=$(grep -a -c "strata prefill timing" "$LOG")
  if [ "$now" -gt "$prev" ]; then grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
  grep -a -E "prefill gemm:|FP32 tiled scorer" "$LOG" | tail -2 >> "$OUT"
done

echo "--- final B needle 32k d50 ---" >> "$OUT"
set_env B
restart_up
docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 50 --url http://127.0.0.1:8090 >> "$OUT" 2>&1

touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
