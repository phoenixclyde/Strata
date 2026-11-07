#!/bin/bash
# W828i: one arm, long-generation decode with the phase ruler.
# Adds per-arm engine-log slicing (the engine's stderr goes to the config's "log" file, not docker logs).
# usage: w828_arm2.sh <arm> <container-config> <container-name> [ready-timeout]
set -u
ARM="$1"; CFG="$2"; NAME="$3"; TO="${4:-900}"
IMG=strata-gfx906:0.2.8
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407
CFG_HOST="${CFG/#\/data\//$DATA/}"
ELOG=$(python3 -c "import json;print(json.load(open('$CFG_HOST')).get('log') or '$DATA/strata-huihui-ud-iq4_xs.log')")
ELOG="${ELOG/#\/data\//$DATA/}"
N0=$(wc -l < "$ELOG" 2>/dev/null || echo 0)

echo "=== ARM2 $ARM  cfg=$CFG  $(date +%H:%M:%S)"
timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && echo "  prod stopped" || echo "  prod stop timeout"
sleep 2
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done

docker run -d --name "$NAME" --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null

sleep 8
if ! docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true; then
  echo "  !! died in 8 s"; docker logs "$NAME" 2>&1 | tail -12 | cut -c1-170; echo "=== ABORT"; exit 3
fi

READY=""
for i in $(seq 1 "$TO"); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then READY=$i; break; fi
  sleep 1
done
echo "  READY=${READY}s"
if [ -z "$READY" ]; then echo "  !! not ready"; docker logs "$NAME" 2>&1 | tail -10 | cut -c1-170; echo "=== ABORT"; exit 4; fi

cd "$TMP" || exit 1
python3 mt_gen.py 8090 "${ARM}_w" /tmp/w828_warm.json dec_corpus.json 16 1 >/dev/null 2>&1 || true

echo "  --- 3 x 512-token greedy ---"
python3 mt_gen.py 8090 "$ARM" "$TMP/w828_${ARM}_512.json" dec_corpus.json 512 3 > "/tmp/w828_${ARM}_512.txt" 2>&1 || true
grep -aE "p[0-9] |MEDIAN" "/tmp/w828_${ARM}_512.txt" | tail -6

# slice this arm's engine stderr out of the shared log
tail -n +$((N0 + 1)) "$ELOG" > "$DATA/w828_${ARM}_engine.log" 2>/dev/null
echo "  --- decode timing (this arm only) ---"
grep -a "strata decode timing" "$DATA/w828_${ARM}_engine.log" | tail -6 | \
  sed -E 's/strata decode timing: ([0-9]+) windows, avg T ([0-9.]+), ([0-9.]+) tokens\/window, ([0-9.]+) ms\/window.*/\1 win T=\2 tok\/win=\3 ms\/win=\4/' | cut -c1-120
echo "  --- spec depth (this arm only) ---"
grep -a "strata serve: spec depth" "$DATA/w828_${ARM}_engine.log" | tail -4 | cut -c1-120
echo "  --- expert cache hit ---"
grep -aoE "expert cache [0-9.]+% hit" "$DATA/w828_${ARM}_engine.log" | tail -4
echo "=== ARM2 $ARM end $(date +%H:%M:%S)"
