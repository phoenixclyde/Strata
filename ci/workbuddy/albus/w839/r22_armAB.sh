#!/bin/bash
# W839-22 A/B 两臂：同一 n3 二进制，A=现役14env，B=TUNED+5非架构env
set -u
IMG=strata-gfx906:0.2.8p2
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407
OUT=$DATA/w839_ab.out
: > "$OUT"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }

run_arm() {
  ARM=$1
  log "=== ARM $ARM start"
  timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && log "  prod stopped"
  sleep 2
  docker rm -f w839ab >/dev/null 2>&1
  docker run -d --name w839ab --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
    "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w839_$ARM.json --port 8090" >/dev/null
  sleep 6
  docker inspect -f '{{.State.Running}}' w839ab 2>/dev/null | grep -q true \
    || { log "  !! container died"; docker logs w839ab 2>&1 | tail -12 | cut -c1-170 | tee -a "$OUT"; return 3; }

  R=""
  for i in $(seq 1 460); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
    sleep 1
  done
  log "  READY=${R}s"
  [ -z "$R" ] && { log "  !! not ready"; docker logs w839ab 2>&1 | tail -12 | cut -c1-170 | tee -a "$OUT"; return 4; }

  log "  --- banner ---"
  docker logs w839ab 2>&1 | grep -aiE 'gfx906|exact speed|recipe is on' | head -6 | cut -c1-220 | tee -a "$OUT"

  log "  --- 引擎进程真实 env（决定性的那一条） ---"
  PID=$(docker exec w839ab bash -lc "pgrep -f 'strata-0.1.54n3' | head -1" 2>/dev/null)
  log "  engine pid=$PID"
  if [ -n "$PID" ]; then
    docker exec w839ab bash -lc "tr '\\0' '\\n' < /proc/$PID/environ | grep '^STRATA_' | sort" 2>/dev/null \
      | sed 's/^/    /' | tee -a "$OUT"
  fi

  log "  --- 测量 ---"
  docker cp "$TMP/ab2.py" w839ab:/tmp/ab2.py >/dev/null 2>&1
  docker exec w839ab python3 /tmp/ab2.py "/data/w839_$ARM.log" "$ARM" 2>&1 | tee -a "$OUT" | tail -14
  log "=== ARM $ARM end"
  docker rm -f w839ab >/dev/null 2>&1
  sleep 3
}

run_arm A
run_arm B

log "=== 恢复生产 ==="
bash "$TMP/r36_restore.sh" >>"$OUT" 2>&1 && log "  restore rc=0"
sleep 5
docker ps --format '{{.Names}} {{.Status}}' | grep strata166 | tee -a "$OUT"
log "ALL DONE"
