#!/bin/bash
C=strata166-407
echo "=== [1] running image ==="
docker inspect $C --format '{{.Config.Image}}' 2>&1
echo
echo "=== [2] css actually served ==="
curl -s --max-time 8 http://127.0.0.1:8090/web/app.css | tail -2
echo "--- cache headers (do we need a hard refresh?) ---"
curl -sI --max-time 8 http://127.0.0.1:8090/web/app.css | grep -iE "cache-control|etag|last-modified|content-length"
echo
echo "=== [3] wait for engine ready ==="
for i in $(seq 1 90); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then echo "READY after ~$((i*3))s"; break; fi
  sleep 3
done
date +%H:%M:%S
curl -s --max-time 6 http://127.0.0.1:8090/health | head -c 220
echo
echo "=== [4] slot count from the engine log ==="
L=/data/strata-huihui-ud-iq4_xs.log
docker exec $C bash -lc "grep -aiE 'expert|slot|GiB' $L 2>/dev/null | tail -3 | cut -c1-150" 2>&1
