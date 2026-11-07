#!/bin/bash
# W839-34 用含调用点的新 n3 重跑 B 臂（TUNED=1 + 5 个非架构 env），跑完恢复生产
set -u
IMG=strata-gfx906:0.2.8p2
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407
OUT=$DATA/w839_b2.out
: > "$OUT"
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }

log "=== ARM B2 start (n3 + TUNED)"
timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && log "  prod stopped"
sleep 2
docker rm -f w839b2 >/dev/null 2>&1
docker run -d --name w839b2 --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w839_B.json --port 8090" >/dev/null
sleep 6
docker inspect -f '{{.State.Running}}' w839b2 2>/dev/null | grep -q true || { log "  !! died"; docker logs w839b2 2>&1|tail -10|cut -c1-170|tee -a "$OUT"; }

R=""
for i in $(seq 1 460); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { R=$i; break; }
  sleep 1
done
log "  READY=${R}s"

log "  --- 引擎日志里的架构横幅（决定性证据） ---"
grep -aE 'gfx906 \(MI50-class\)' $DATA/w839_B.log 2>/dev/null | head -4 | cut -c1-230 | tee -a "$OUT"

log "  --- 测量 ---"
docker cp "$TMP/ab2.py" w839b2:/tmp/ab2.py >/dev/null 2>&1
docker exec w839b2 python3 /tmp/ab2.py "/data/w839_B.log" "B2" 2>&1 | tee -a "$OUT" | tail -12

docker rm -f w839b2 >/dev/null 2>&1
sleep 3
log "=== 恢复生产 ==="
bash "$TMP/r36_restore.sh" >>"$OUT" 2>&1 && log "  restore rc=0"
sleep 4
docker ps --format '{{.Names}} {{.Status}}' | grep strata166 | tee -a "$OUT"
log "ALL DONE"
