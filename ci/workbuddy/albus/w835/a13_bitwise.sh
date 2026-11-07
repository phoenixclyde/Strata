#!/bin/bash
# W835c: are the 4 gfx12-bitwise decode switches also wins on gfx906?
# arms: base -> +LANECELL -> +LANECELL+TSUM -> +all4 -> base2
set -u
OUT=/home/albus/strata166/data/w835_bitwise.out
: > "$OUT"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$OUT"; }
IMG=strata-gfx906:0.2.8p2
BASE=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json

L1="STRATA_ATTN_LANECELL=1"
L2="STRATA_ATTN_LANECELL=1 STRATA_TSUM=1"
L4="STRATA_ATTN_LANECELL=1 STRATA_TSUM=1 STRATA_ATTN_MERGE_V2=1 STRATA_EXPDEC=1"

restore_prod() {
  say "restore prod"
  docker rm -f w835 >/dev/null 2>&1 || true
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
  local cfg="/home/albus/strata166/data/w835_${tag}.json"
  python3 - "$BASE" "$cfg" "$extra" "$tag" <<'PY'
import json, sys
src, dst, extra, tag = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
c = json.load(open(src))
env = dict(c.get("env") or {})
added = {}
for kv in extra.split():
    k, v = kv.split("=", 1)
    env[k] = v
    added[k] = v
c["env"] = env
c["log"] = "/data/w835_%s.log" % tag
json.dump(c, open(dst, "w"), indent=2)
print("cfg", dst, "env", len(env), "added", sorted(added))
PY
  say "arm $tag start (env+$(echo $extra | wc -w))"
  docker rm -f w835 >/dev/null 2>&1 || true
  docker run -d --name w835 --ipc host --security-opt label=disable \
    --device=/dev/kfd --device=/dev/dri --group-add video \
    -p 8090:8090 -v /models:/models:ro -v /home/albus/strata166/data:/data \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
    $IMG bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/w835_${tag}.json --port 8090" >/dev/null

  local ok=0
  for i in $(seq 1 140); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then ok=1; say "  ready ~$((i*3))s"; break; fi
    sleep 3
  done
  if [ "$ok" -ne 1 ]; then
    say "  ARM $tag NOT READY"
    docker logs --tail 25 w835 2>&1 | tee -a "$OUT"
    grep -aE "non-finite|abort|error" /home/albus/strata166/data/w835_${tag}.log 2>/dev/null | tail -4 | tee -a "$OUT"
    return 1
  fi

  docker cp /home/albus/strata166/tmp/ab2.py w835:/tmp/ab2.py 2>/dev/null
  docker exec w835 env DEC_REPS=8 RD_REPS=3 python3 /tmp/ab2.py "/data/w835_${tag}.log" "$tag" 2>&1 | tee -a "$OUT"
  say "arm $tag done"
  docker rm -f w835 >/dev/null 2>&1 || true
  sleep 4
  return 0
}

run_arm base  ""  || say "base failed"
run_arm tL    "$L1" || say "tL failed"
run_arm tLT   "$L2" || say "tLT failed"
run_arm tL4   "$L4" || say "tL4 failed"
run_arm base2 ""  || say "base2 failed"

restore_prod
say "ALL DONE"
