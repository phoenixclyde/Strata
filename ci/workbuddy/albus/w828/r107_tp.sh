#!/bin/bash
# W828o: start one config, warm up, then measure TTFT. Same harness for every arm.
# usage: r106_ttft_arm.sh <tag>   (tag: tp = prod copy, tq = prod + PREFILL_MMQ=0)
set -u
TAG="tp"
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407
IMG=strata-gfx906:0.2.8
CFG=/data/w828_${TAG}.json

timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && echo "  prod stopped"
sleep 2
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run -d --name "w828$TAG" --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
sleep 8
docker inspect -f '{{.State.Running}}' "w828$TAG" 2>/dev/null | grep -q true || { echo "!! died"; docker logs "w828$TAG" 2>&1 | tail -8 | cut -c1-150; exit 3; }
for i in $(seq 1 600); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  READY=${i}s"; break; }; sleep 1; done
echo "  --- TTFT: 3 warm-ups then 1151/2213/4345 x2 ---"
cd "$TMP" && timeout 1200 python3 w828_ttft3.py 8090 1200,2400,4800 2 3 2>&1 | tail -14
echo "=== arm $TAG end $(date +%H:%M:%S)"
