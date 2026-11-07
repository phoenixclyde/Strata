#!/bin/bash
# Recreate the production container with the ONE flag that was dropped, everything else
# unchanged (verified by diff_container.py: only Ulimits differed).
set -uo pipefail
C=strata166-407
docker stop "$C" >/dev/null 2>&1 || true
docker rm -f "$C" >/dev/null 2>&1 || true
# rename the previous instance out of the way so it can be diffed / rolled back to
docker ps -a --format '{{.Names}}' | grep -qx 'strata166-407-old2' && docker rm -f strata166-407-old2 >/dev/null 2>&1

docker run -d --name "$C" \
  --device /dev/kfd --device /dev/dri --group-add video \
  --ulimit memlock=-1:-1 \
  --restart unless-stopped -p 8090:8090 \
  -v /home/albus/strata166/data:/data -v /models:/models:ro \
  --shm-size 64m --ipc host --security-opt label=disable \
  strata-gfx906:0.2.11-101 \
  bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >/dev/null
echo "run rc=$?"

for i in $(seq 1 18); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after $((i*10))s"; break;; esac
  sleep 10
done

echo "ulimit_l=$(docker exec $C sh -c 'ulimit -l' || true)"
P=$(docker inspect -f '{{.State.Pid}}' "$C")
grep VmLck /proc/$P/status || true
docker inspect -f 'container={{.Id}} img={{.Config.Image}} restarts={{.RestartCount}} started={{.State.StartedAt}} ulimits={{json .HostConfig.Ulimits}}' "$C" | cut -c1-160
