#!/bin/bash
# W834b：数值债 5 项分项（每项各关一次）对基线 E0
set -u
OUT=/home/albus/strata166/data/w834_klbisect.out
: > "$OUT"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }
IMG=strata-gfx906:0.2.8p2
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407

restore_prod() {
  say "restore prod"
  docker rm -f w834b >/dev/null 2>&1 || true
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

mkdir -p "$DATA/w834kl"
cp -f "$DATA/w833kl/E0.tsv" "$DATA/w834kl/E0.tsv" 2>/dev/null && say "baseline E0 copied"

say "=== 生产快照（改动前） ==="
python3 "$TMP/state_q.py" --no-probe 2>&1 | tee -a "$OUT"

say "stop prod"
docker rm -f "$PROD" >/dev/null 2>&1 || true
sleep 3

run_arm() {
  local tag="$1"
  local cfg="$DATA/w834_${tag}.json"
  local tsv="$DATA/w834kl/$(echo $tag | tr a-z A-Z).tsv"
  say "arm $tag start"
  rm -f "$tsv"
  docker rm -f w834b >/dev/null 2>&1 || true
  docker run -d --name w834b --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w834_${tag}.json --port 8090" >/dev/null

  local ok=0
  for i in $(seq 1 150); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "  ready ~$((i*3))s"; break; fi
    sleep 3
  done
  if [ "$ok" -ne 1 ]; then
    say "  ARM $tag NOT READY"; docker logs --tail 15 w834b 2>&1 | tee -a "$OUT"; docker rm -f w834b >/dev/null 2>&1; return 1
  fi
  cd "$TMP" || return 1
  python3 "$TMP/kl_send.py" 8090 "$TMP/kl_long.json" "$tag" 900 2>&1 | tail -1 | tee -a "$OUT"
  say "  $tag tsv_lines=$(wc -l < "$tsv" 2>/dev/null || echo 0)"
  docker rm -f w834b >/dev/null 2>&1 || true
  sleep 3
  return 0
}

for t in rt0 kvfp16 pf0 simt0 hcq0; do
  run_arm "$t" || say "$t failed"
done

restore_prod
say "=== 生产快照（改动后） ==="
for i in $(seq 1 60); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 5; done
python3 "$TMP/state_q.py" --no-probe 2>&1 | tee -a "$OUT"
say "ALL DONE"
