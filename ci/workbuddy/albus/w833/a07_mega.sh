#!/bin/bash
# W833 P1-a：gfx1151 剩余开关的 mega-arm（base vs base+10 项）
set -u
OUT=/home/albus/strata166/data/w833_mega.out
: > "$OUT"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }
IMG=strata-gfx906:0.2.8p2
BASE=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json

MEGA="STRATA_GDN_CONVL2=1 STRATA_GDN_NOY=1 STRATA_CVEC_FUSE=1 STRATA_HCD_EXACT=1 \
STRATA_TOPK_REG_MIN_BLOCKS=4096 STRATA_Q8_PACKED=1 STRATA_Q6_PACKED=1 STRATA_TSUM=1 \
STRATA_QFUSE=1 STRATA_PLE_BATCH=1"

restore_prod() {
  say "restore prod"
  docker rm -f w833 >/dev/null 2>&1 || true
  docker rm -f strata166-407 >/dev/null 2>&1 || true
  docker run -d --name strata166-407 --restart unless-stopped \
    --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    $IMG bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null
  say "prod started"
}
trap 'say "TRAP"; restore_prod; exit 1' INT TERM

say "=== 生产快照（改动前） ==="
python3 /home/albus/strata166/tmp/state_q.py --no-probe 2>&1 | tee -a "$OUT"

say "stop prod"
docker rm -f strata166-407 >/dev/null 2>&1 || true
sleep 3

run_arm() {
  local tag="$1" extra="$2"
  local cfg="/home/albus/strata166/data/w833_${tag}.json"
  python3 - "$BASE" "$cfg" "$extra" <<'PY'
import json, sys
src, dst, extra = sys.argv[1], sys.argv[2], sys.argv[3]
c = json.load(open(src))
env = dict(c.get("env") or {})
added = {}
for kv in extra.split():
    k, v = kv.split("=", 1)
    env[k] = v
    added[k] = v
c["env"] = env
c["log"] = "/data/w833_%s.log" % dst.rsplit("_", 1)[-1].replace(".json", "")
json.dump(c, open(dst, "w"), indent=2)
print("cfg", dst, "env", len(env), "added", len(added), sorted(added))
PY
  say "arm $tag start (env+$(echo $extra | wc -w))"
  docker rm -f w833 >/dev/null 2>&1 || true
  docker run -d --name w833 --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    $IMG bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w833_${tag}.json --port 8090" >/dev/null

  local ok=0
  for i in $(seq 1 140); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "  ready ~$((i*3))s"; break; fi
    sleep 3
  done
  if [ "$ok" -ne 1 ]; then
    say "  ARM $tag NOT READY"
    docker logs --tail 30 w833 2>&1 | tee -a "$OUT"
    return 1
  fi

  docker cp /home/albus/strata166/tmp/ab2.py w833:/tmp/ab2.py
  docker exec w833 env DEC_REPS=8 RD_REPS=3 python3 /tmp/ab2.py "/data/w833_${tag}.log" "$tag" 2>&1 | tee -a "$OUT"
  say "arm $tag done"
  docker rm -f w833 >/dev/null 2>&1 || true
  sleep 4
  return 0
}

run_arm base "" || say "base failed"
run_arm mega "$MEGA" || say "mega failed"

restore_prod
say "=== 生产快照（改动后） ==="
for i in $(seq 1 60); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 5; done
python3 /home/albus/strata166/tmp/state_q.py --no-probe 2>&1 | tee -a "$OUT"
say "ALL DONE"
