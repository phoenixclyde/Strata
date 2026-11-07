#!/bin/bash
# W833 P0-c：四臂 KL 采集（e0 / e0b 地板 / emmq / egdn），结束后自动恢复生产
set -u
OUT=/home/albus/strata166/data/w833_kl.out
: > "$OUT"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }
IMG=strata-gfx906:0.2.8p2
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407

restore_prod() {
  say "restore prod"
  docker rm -f w833kl >/dev/null 2>&1 || true
  docker rm -f "$PROD" >/dev/null 2>&1 || true
  docker run -d --name "$PROD" --restart unless-stopped \
    --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    "$IMG" bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
  say "prod started"
}
trap 'say TRAP; restore_prod; exit 1' INT TERM

say "=== 生产快照（改动前） ==="
python3 "$TMP/state_q.py" --no-probe 2>&1 | tee -a "$OUT"

say "stop prod"
docker rm -f "$PROD" >/dev/null 2>&1 || true
sleep 3

run_arm() {
  local tag="$1" cfg="$2" tsv="$3"
  say "arm $tag start"
  docker rm -f w833kl >/dev/null 2>&1 || true
  docker run -d --name w833kl --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $cfg --port 8090" >/dev/null

  local ok=0
  for i in $(seq 1 150); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "  ready ~${i}s"; break; fi
    sleep 3
  done
  if [ "$ok" -ne 1 ]; then
    say "  ARM $tag NOT READY"; docker logs --tail 20 w833kl 2>&1 | tee -a "$OUT"; return 1
  fi

  rm -f "$tsv"
  cd "$TMP" || return 1
  python3 "$TMP/kl_send.py" 8090 "$TMP/kl_long.json" "$tag" 900 2>&1 | tail -2 | tee -a "$OUT"
  local L M
  L=$(wc -l < "$tsv" 2>/dev/null || echo 0)
  M=$(md5sum "$tsv" 2>/dev/null | awk '{print $1}')
  say "  $tag lines=$L md5=$M"
  docker rm -f w833kl >/dev/null 2>&1 || true
  sleep 4
  return 0
}

run_arm e0   /data/w833_kle0.json   /data/w833kl/E0.tsv
run_arm e0b  /data/w833_kle0b.json  /data/w833kl/E0b.tsv
run_arm emmq /data/w833_klemmq.json /data/w833kl/EM.tsv
run_arm egdn /data/w833_klegdn.json /data/w833kl/EG.tsv

restore_prod
say "=== 生产快照（改动后） ==="
for i in $(seq 1 60); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 5; done
python3 "$TMP/state_q.py" --no-probe 2>&1 | tee -a "$OUT"
say "ALL DONE"
