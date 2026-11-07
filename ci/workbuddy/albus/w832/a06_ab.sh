#!/bin/bash
# W832 P0-b：0.1.53 vs 0.1.54n2 同源 A/B（同镜像 0.2.8p2、同 33 args / 14 env，只差 exe）
set -u
OUT=/home/albus/strata166/data/w832_ab_engine.out
: > "$OUT"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }
IMG=strata-gfx906:0.2.8p2
BASE=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json

restore_prod() {
  say "restore prod"
  docker rm -f w832ab >/dev/null 2>&1 || true
  docker rm -f strata166-407 >/dev/null 2>&1 || true
  docker run -d --name strata166-407 --restart unless-stopped \
    --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    $IMG bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
  say "prod container started"
}
trap 'say "TRAP"; restore_prod; exit 1' INT TERM

say "=== 生产快照（改动前） ==="
python3 /home/albus/strata166/tmp/state.py 2>&1 | tee -a "$OUT"

say "stop prod"
docker rm -f strata166-407 >/dev/null 2>&1 || true
sleep 3

run_arm() {
  local tag="$1" exe="$2"
  local cfg="/home/albus/strata166/data/w832_${tag}.json"
  python3 - "$BASE" "$cfg" "$exe" "/data/w832_${tag}.log" <<'PY'
import json, sys
src, dst, exe, log = sys.argv[1:5]
c = json.load(open(src)); c["exe"] = exe; c["log"] = log
json.dump(c, open(dst, "w"), indent=2)
print("cfg", dst, "exe", exe, "args", len(c["args"]), "env", len(c["env"]))
PY
  say "arm $tag start ($exe)"
  docker rm -f w832ab >/dev/null 2>&1 || true
  docker run -d --name w832ab --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    $IMG bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w832_${tag}.json --port 8090" >/dev/null

  local ok=0
  for i in $(seq 1 140); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "  ready ~$((i*3))s"; break; fi
    sleep 3
  done
  if [ "$ok" -ne 1 ]; then
    say "  ARM $tag NOT READY"
    docker logs --tail 25 w832ab 2>&1 | tee -a "$OUT"
    return 1
  fi

  docker cp /home/albus/strata166/tmp/ab_engine.py w832ab:/tmp/ab_engine.py
  docker exec w832ab python3 /tmp/ab_engine.py "/data/w832_${tag}.log" "$tag" 2>&1 | tee -a "$OUT"
  say "arm $tag done"
  docker rm -f w832ab >/dev/null 2>&1 || true
  sleep 4
  return 0
}

run_arm a153 /data/bin/strata-0.1.53 || say "a153 failed"
run_arm b154n2 /data/bin/strata-0.1.54n2 || say "b154n2 failed"

restore_prod
say "=== 生产快照（改动后） ==="
for i in $(seq 1 60); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break
  sleep 5
done
python3 /home/albus/strata166/tmp/state.py 2>&1 | tee -a "$OUT"
say "ALL DONE"
