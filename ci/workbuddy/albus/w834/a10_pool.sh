#!/bin/bash
# W834：--pool-workers 默认(0=20) vs 13，两臂同镜像同配置，只差这一个 arg
set -u
OUT=/home/albus/strata166/data/w834_pool.out
: > "$OUT"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }
IMG=strata-gfx906:0.2.8p2
BASE=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
TMP=/home/albus/strata166/tmp
PROD=strata166-407

restore_prod() {
  say "restore prod"
  docker rm -f w834 >/dev/null 2>&1 || true
  docker rm -f "$PROD" >/dev/null 2>&1 || true
  docker run -d --name "$PROD" --restart unless-stopped \
    --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    "$IMG" bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
  say "prod started"
}
trap 'say TRAP; restore_prod; exit 1' INT TERM

say "=== 生产快照（改动前） ==="
python3 "$TMP/state_q.py" --no-probe 2>&1 | tee -a "$OUT"

say "stop prod"
docker rm -f "$PROD" >/dev/null 2>&1 || true
sleep 3

run_arm() {
  local tag="$1" pw="$2"
  local cfg="$DATA/w834_${tag}.json"
  python3 - "$BASE" "$cfg" "$tag" "$pw" <<'PY'
import json, sys
src, dst, tag, pw = sys.argv[1:5]
c = json.load(open(src))
a = [x for x in c["args"]]
if pw not in ("", "default"):
    a += ["--pool-workers", pw]
c["args"] = a
c["log"] = "/data/w834_%s.log" % tag
json.dump(c, open(dst, "w"), ensure_ascii=False, indent=1)
print("cfg", dst, "args", len(a), "pool-workers", pw)
PY
  say "arm $tag start (pool-workers=$pw)"
  docker rm -f w834 >/dev/null 2>&1 || true
  docker run -d --name w834 --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v "$DATA":/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w834_${tag}.json --port 8090" >/dev/null

  local ok=0
  for i in $(seq 1 150); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "  ready ~${i}s"; break; fi
    sleep 3
  done
  if [ "$ok" -ne 1 ]; then
    say "  ARM $tag NOT READY"; docker logs --tail 20 w834 2>&1 | tee -a "$OUT"; return 1
  fi
  say "  workers: $(docker exec w834 bash -lc "grep -a 'expert-pool workers' /data/w834_${tag}.log | tail -1" | cut -c1-80)"
  docker cp "$TMP/ab2.py" w834:/tmp/ab2.py
  docker exec w834 env DEC_REPS=8 RD_REPS=3 python3 /tmp/ab2.py "/data/w834_${tag}.log" "$tag" 2>&1 | tee -a "$OUT"
  say "arm $tag done"
  docker rm -f w834 >/dev/null 2>&1 || true
  sleep 4
  return 0
}

run_arm base default || say "base failed"
run_arm pw13 13 || say "pw13 failed"

restore_prod
say "=== 生产快照（改动后） ==="
for i in $(seq 1 60); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 5; done
python3 "$TMP/state_q.py" --no-probe 2>&1 | tee -a "$OUT"
say "ALL DONE"
