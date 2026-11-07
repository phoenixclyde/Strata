#!/bin/bash
# W828k3: prefill math-path A/B by TTFT (no decode measurement).
# usage: r96_ttft_arm.sh <tag> [extra_env_json_fragment]
set -u
TAG="ts"
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407
IMG=strata-gfx906:0.2.8
CFG=/data/w828_${TAG}.json

timeout 90 docker stop -t 25 "$PROD" >/dev/null 2>&1 && echo "  prod stopped" || echo "  prod stop timeout"
sleep 2
for c in $(docker ps -aq --filter "name=w828"); do docker rm -f "$c" >/dev/null 2>&1; done
docker run -d --name "w828$TAG" --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
sleep 8
docker inspect -f '{{.State.Running}}' "w828$TAG" 2>/dev/null | grep -q true || { echo "!! died"; docker logs "w828$TAG" 2>&1 | tail -10 | cut -c1-160; exit 3; }
for i in $(seq 1 600); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  READY=${i}s"; break; }; sleep 1; done
echo "  --- prefill math path banner ---"
ELOG=$(python3 -c "import json;print(json.load(open('$DATA/w828_${TAG}.json')).get('log'))" | sed 's#^/data/#'"$DATA"'/#')
grep -a "prefill\|K-quant prompt kernels" "$ELOG" 2>/dev/null | tail -4 | cut -c1-170
echo "  --- TTFT probe (seeds identical to the baseline run) ---"
cd "$TMP" && timeout 600 python3 w828_ttft2.py 8090 8000,16000 2 2>&1 | tail -16
echo "=== arm $TAG end $(date +%H:%M:%S)"
