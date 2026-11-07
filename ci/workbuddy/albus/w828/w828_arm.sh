#!/bin/bash
# W828: one arm = stop production -> start a one-off container -> wait ready -> decode + read sweep.
# usage: w828_arm.sh <arm> <container-config-path> <container-name> [ready-timeout] [measure 0|1]
set -u
ARM="$1"; CFG="$2"; NAME="$3"; TO="${4:-900}"; MEAS="${5:-1}"
IMG=strata-gfx906:0.2.4p4
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
LOG=$DATA/w828_arm_${ARM}.log
PROD=strata166-407

echo "=== ARM $ARM  cfg=$CFG  $(date +%H:%M:%S)"
timeout 90 docker stop -t 20 "$PROD" >/dev/null 2>&1 && echo "  production stopped" || echo "  production stop timeout/absent"
sleep 2
echo "  MemAvailable: $(awk '/MemAvailable/{print int($2/1024)" MiB"}' /proc/meminfo)"

docker rm -f "$NAME" >/dev/null 2>&1
# W828: every arm publishes :8090, and the previous arm's container is still running here
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run -d --name "$NAME" \
  --ulimit memlock=-1 --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models -v "$DATA":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
echo "  container up $(date +%H:%M:%S)"

sleep 8
docker exec "$NAME" test -f "$CFG" 2>/dev/null || echo "  WARNING: $CFG missing inside the container"
if ! docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true; then
  echo "  !! container died within 8 s - tail:"
  docker logs "$NAME" 2>&1 | tail -16 | cut -c1-170
  echo "=== ARM $ARM ABORTED"
  exit 3
fi

READY=""
for i in $(seq 1 "$TO"); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then READY=$i; break; fi
  sleep 1
done
echo "  READY=${READY}s"
docker logs "$NAME" > "$LOG" 2>&1

echo "  --- version / engine line ---"
grep -a -E "strata engine 0|engine started|native pack:|expert cache [0-9]+ slots|expert cache auto" "$LOG" | head -4 | cut -c1-190
echo "  --- engine banner ---"
grep -a -iE "strata engine|engine version|build 0\.1" "$LOG" | head -3 | cut -c1-190

if [ "$MEAS" = "1" ] && [ -n "$READY" ]; then
  cd "$TMP" || exit 1
  echo "  --- decode 5 x 128 (T=0, warm 2 in mt_read follows) ---"
  python3 mt_gen.py 8090 "$ARM" "$DATA/w828_${ARM}_dec.json" dec_corpus.json 128 5 > /tmp/w828_${ARM}_dec.txt 2>&1 || true
  grep -a -iE "ptok=|tok/s|ms/tok" /tmp/w828_${ARM}_dec.txt | tail -6
  echo "  --- read sweep 1500/3000/6000, warm 2 ---"
  python3 mt_read.py 8090 "$ARM" "$DATA/w828_${ARM}_read.json" 1500,3000,6000 1 kl_pool.json 0 2 > /tmp/w828_${ARM}_read.txt 2>&1 || true
  tail -6 /tmp/w828_${ARM}_read.txt
  docker logs "$NAME" > "$LOG" 2>&1
fi

echo "  --- phase ---"
grep -a "strata prefill timing" "$LOG" | tail -3 | cut -c1-175
echo "  --- arena / slots ---"
grep -a -E "expert arena:|expert cache [0-9]+ slots|VRAM free|hit rate" "$LOG" | tail -3 | cut -c1-165
echo "=== ARM $ARM end $(date +%H:%M:%S)"
