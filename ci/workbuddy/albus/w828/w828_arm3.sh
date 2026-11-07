#!/bin/bash
# W828f: the --batch 2 arm. One request first (does one stream regress?), then two at once
# (does the summed throughput beat one stream enough to pay for the smaller cache?).
set -u
ARM="$1"; CFG="$2"; NAME="$3"; TO="${4:-900}"
IMG=strata-gfx906:0.2.8
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407

echo "=== ARM3 $ARM  cfg=$CFG  $(date +%H:%M:%S)"
timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && echo "  prod stopped"
sleep 2
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run -d --name "$NAME" --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
sleep 8
docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true || { echo "  !! died"; docker logs "$NAME" 2>&1|tail -12|cut -c1-170; exit 3; }

R=""
for i in $(seq 1 "$TO"); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then R=$i; break; fi
  sleep 1
done
echo "  READY=${R}s"
[ -n "$R" ] || { docker logs "$NAME" 2>&1|tail -10|cut -c1-170; exit 4; }

echo "  --- pool / slots at start ---"
docker logs "$NAME" 2>&1 | grep -aE "batch|slot|filling the GPU" | head -6 | cut -c1-185

cd "$TMP" || exit 1
echo "  --- one stream (does it regress?) ---"
python3 mt_gen.py 8090 "${ARM}_1" "$TMP/w828_${ARM}_single.json" dec_corpus.json 512 2 > "/tmp/w828_${ARM}_single.txt" 2>&1 || true
grep -aE "p[0-9] |MEDIAN" "/tmp/w828_${ARM}_single.txt" | tail -4

echo "  --- two streams at once ---"
python3 "$TMP/mt_gen2.py" 8090 "$ARM" "$TMP/w828_${ARM}_dual.json" dec_corpus.json 512 2 3 > "/tmp/w828_${ARM}_dual.txt" 2>&1 || true
grep -aE "round|MEDIAN SUM" "/tmp/w828_${ARM}_dual.txt" | tail -5

docker logs "$NAME" > "$TMP/w828_${ARM}_batch.log" 2>&1
echo "  --- decode timing (last 4) ---"
grep -a "strata decode timing" "$TMP/w828_${ARM}_batch.log" | tail -4 | sed -E 's/.*windows, avg T ([0-9.]+), ([0-9.]+) tokens\/window, ([0-9.]+) ms\/window.*GPU-reach wait ([0-9.]+).*/\1 T  \2 tk\/win  \3 ms\/win  reach \4/' 
echo "  --- cache ---"
grep -aE "expert cache [0-9]+ slots|hit rate" "$TMP/w828_${ARM}_batch.log" | tail -3 | cut -c1-150
echo "=== ARM3 $ARM end $(date +%H:%M:%S)"
