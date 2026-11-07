#!/bin/sh
# W793：0.2.4p3 镜像（rocBLAS 接线 + max-ilp）三臂 A/B
#   A = 基（只换镜像，env 不变）        -> 隔离 max-ilp + 接线
#   B = A + STRATA_ROCBLAS_TUNING        -> 隔离解题表（同一二进制，只改 env）
#   C = A + STRATA_SELECT_SIMT=1         -> 隔离 FP32 分块 scorer
# 全程带 STRATA_PREFILL_TIMING=1 取相位账；对照是旧镜像带仪器的 36,016 ms（W792 F 臂中位）。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w793_ab_$TS.txt
BAK=$CFG.bak_w793_$TS
CONT=strata166-407
IMG=strata-gfx906:0.2.4p3
TABLE=/data/gfx906-rocblas-5.5.0.txt
OKFLAG=/tmp/w793_ab_done

rm -f "$OKFLAG"

ensure_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 240); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 20
}

restore() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY: keep container up $(date +%H:%M:%S) ===" >> "$OUT"
    ensure_up
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

set_env() {   # $1 = arm letter
  python3 - "$CFG" "$1" "$TABLE" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm, table = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(cfg))
e = {k: v for k, v in d.get('env', {}).items() if k not in ('STRATA_PREFILL_TIMING', 'STRATA_ROCBLAS_TUNING', 'STRATA_SELECT_SIMT')}
e['STRATA_PREFILL_TIMING'] = '1'
if arm == 'B': e['STRATA_ROCBLAS_TUNING'] = table
if arm == 'C': e['STRATA_SELECT_SIMT'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('arm', arm, 'env', sorted(e.items()))
PY
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK" >> "$OUT"
md5sum "$CFG" >> "$OUT"
echo "image_before=$(docker inspect -f '{{.Config.Image}}' $CONT 2>/dev/null)" >> "$OUT"
echo "governor=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c | tr '\n' ' ')" >> "$OUT"

trap 'restore' EXIT HUP INT TERM

# ---- 换镜像（同名容器重建；原容器 rename 成 .bak_w793 便于回滚）
echo "=== swap image $(date +%H:%M:%S) ===" >> "$OUT"
docker stop -t 40 "$CONT" >> "$OUT" 2>&1
docker rename "$CONT" "$CONT.bak_w793" >> "$OUT" 2>&1
docker run -d --name "$CONT" \
  --device /dev/kfd --device /dev/dri \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -p 8090:8090 --network bridge --ipc host --group-add video \
  --restart unless-stopped \
  "$IMG" /bin/bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
echo "new_container=$(docker inspect -f '{{.Config.Image}}' $CONT 2>/dev/null)" >> "$OUT"

# 新镜像起不来就立刻回滚到原容器（不等到最后）
up=0
for i in $(seq 1 240); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then up=1; echo "new image healthy ${i}s" >> "$OUT"; break; fi
  sleep 1
done
if [ "$up" = "0" ]; then
  echo "=== NEW IMAGE DID NOT COME UP: rollback $(date +%H:%M:%S) ===" >> "$OUT"
  docker logs --tail 40 "$CONT" >> "$OUT" 2>&1
  docker rm -f "$CONT" >> "$OUT" 2>&1
  docker rename "$CONT.bak_w793" "$CONT" >> "$OUT" 2>&1
  docker start "$CONT" >> "$OUT" 2>&1
  for i in $(seq 1 240); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "rolled back, ready ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  touch "$OKFLAG"
  echo "ROLLED_BACK $(date +%H:%M:%S)" >> "$OUT"
  exit 0
fi
sleep 15

for arm in A B A B C C; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_env "$arm"
  ensure_up
  prev=$(grep -a -c "strata prefill timing" "$LOG")
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  now=$(grep -a -c "strata prefill timing" "$LOG")
  if [ "$now" -gt "$prev" ]; then grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
  grep -a -E "rocBLAS tuning enabled|FP32 tiled scorer" "$LOG" | tail -1 >> "$OUT"
  if [ "$arm" = "B" ]; then
    echo "--- B needle 32k d50 ---" >> "$OUT"
    docker exec "$CONT" python3 /src/tools/needle_bench.py --lengths 32k --depths 50 --url http://127.0.0.1:8090 >> "$OUT" 2>&1
  fi
done

touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
