#!/bin/bash
# W828g: one KL arm — N prompts (each scores a few positions through the verify window), dumps accumulate.
set -u
ARM="$1"; CFG="$2"; NAME="$3"; TSV="$4"; NP="${5:-8}"; TO="${6:-900}"
IMG=strata-gfx906:0.2.8
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407

echo "=== KLARM $ARM  $(date +%H:%M:%S)  prompts=$NP  tsv=$TSV"
timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && echo "  prod stopped"
sleep 2
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run -d --name "$NAME" --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
sleep 8
docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true || { echo "  !! died"; docker logs "$NAME" 2>&1|tail -10|cut -c1-170; exit 3; }
R=""
for i in $(seq 1 "$TO"); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
  sleep 1
done
echo "  READY=${R}s"
cd "$TMP" || exit 1
python3 "$TMP/kl_send_multi.py" 8090 "$TMP/kl_multi.json" "$ARM" 1 2>&1 | tail -9
sleep 4
echo "  LOGPOS: $(wc -l < "$TSV" 2>/dev/null || echo 0) lines"
md5sum "$TSV" 2>/dev/null || true
echo "=== KLARM $ARM end $(date +%H:%M:%S)"
