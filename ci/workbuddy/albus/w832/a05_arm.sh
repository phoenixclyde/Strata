#!/bin/bash
# W832 P0-a：单次启动内交替重判 spec_min_p / pcie_frac
# 结构：停生产 -> 起实验容器 -> 开测 -> 收拾 -> 无论成败恢复生产
set -u
LOG=/home/albus/strata166/data/w832_sweep.out
: > "$LOG"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

restore_prod() {
  say "restore prod"
  docker rm -f w832 >/dev/null 2>&1 || true
  docker rm -f strata166-407 >/dev/null 2>&1 || true
  docker run -d --name strata166-407 --restart unless-stopped \
    --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    strata-gfx906:0.2.8p2 bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
  say "prod container started"
}
trap 'say "TRAP: restoring"; restore_prod; exit 1' INT TERM

say "stop prod"
docker rm -f strata166-407 >/dev/null 2>&1 || true
sleep 3

say "start w832 (DECODE_TIMING=1)"
docker rm -f w832 >/dev/null 2>&1 || true
docker run -d --name w832 --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  strata-gfx906:0.2.8p2 bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/w832_tune.json --port 8090' >/dev/null

say "wait ready (max 420 s)"
ok=0
for i in $(seq 1 140); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "ready after ~$((i*3))s"; break; fi
  sleep 3
done
if [ "$ok" -ne 1 ]; then say "NOT READY"; docker logs --tail 20 w832 2>&1 | tee -a "$LOG"; restore_prod; exit 1; fi

docker cp /home/albus/strata166/tmp/sweep.py w832:/tmp/sweep.py
say "sweep start"
docker exec w832 python3 /tmp/sweep.py 2>&1 | tee -a "$LOG"
say "sweep end rc=$?"

restore_prod
say "ALL DONE"
