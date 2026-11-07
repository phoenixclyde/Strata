#!/bin/bash
# W1041 window: does the warp-per-group quantizer rescue DP4A?
#   ctl = b12180 (no restart) | b = pa5 + ATTN_DP4A (quant fixed, bit-identical codes)
# Two restarts (arm + restore).
set -u
W=/home/albus/strata166/tmp/w1039
OLD=/home/albus/strata166/tmp/w1037
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
BASE_CT=/data/bin/strata-0.1.57-b12180
PA5_CT=/data/bin/strata-0.1.57-pa5
WANT_BASE=d24f8293b575fbcee6c097239d9599cb
WANT_PA5=c639b60c5981267c8d82ee3a4b0750e8
WANT_CFG=5e9b81e2f66ca48999766d2ae0201fb6
PROG=$W/window3.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

wait_health() {
  local t0=$1 t=$1
  while [ "$t" -gt 0 ]; do
    if curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"'; then
      log "health ok after $(( t0 - t ))s"; return 0
    fi
    sleep 3; t=$((t - 3))
  done
  return 1
}

apply_cfg() {
  python3 - "$CFG" "$1" "$2" <<'PY' || return 1
import io, json, sys
p, exe, spec = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
env = d.get("env") or {}
for k in ("STRATA_GFX906_ATTN_DP4A", "STRATA_GFX906_ATTN_DPP",
          "STRATA_GFX906_ATTN_LDS_PAD", "STRATA_GFX906_ROUTE_DPP",
          "STRATA_GFX906_Q8_GATHER8"):
    env.pop(k, None)
for item in [x for x in spec.split(";") if x]:
    k, v = item.split("=", 1)
    env[k] = v
d["env"] = env
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("exe=%s opts=%s" % (exe, {k: v for k, v in env.items() if k.startswith("STRATA_GFX906_ATTN")}))
PY
}

restore() {
  local rc=$?
  if [ -f "$W/cfg_window3.bak" ]; then
    cp -f "$W/cfg_window3.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_window3.bak" "$CFG"
    [ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || sudo -n cp -f "$W/cfg_window3.bak" "$CFG"
    log "RESTORE (rc=$rc) cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
    [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" = "true" ] || docker start $C >/dev/null 2>&1
    wait_health 420 || log "WARN health did not return"
  fi
}

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$BASE_CT" ] || fail "production is not b12180"
md5sum "$DATA/bin/strata-0.1.57-pa5" | grep -q $WANT_PA5 || fail "pa5 md5"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config baseline"
cp -f "$CFG" "$W/cfg_window3.bak"
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== arm ctl 1/2 ==="
python3 "$W/ab_w1039.py" "$W/w3_ctl.json" ctl >> "$PROG" 2>&1 || fail "ctl1"
date +%s%N > "$OLD/salt"
log "=== arm ctl 2/2 ==="
python3 "$W/ab_w1039.py" "$W/w3_ctl2.json" ctl2 >> "$PROG" 2>&1 || fail "ctl2"

log "=== arm pa5+DP4A ==="
docker stop -t 30 $C >/dev/null || fail "stop"
apply_cfg "$PA5_CT" "STRATA_GFX906_ATTN_DP4A=1" >> "$PROG" 2>&1 || fail "config"
docker start $C >/dev/null || fail "start"
wait_health 420 || fail "pa5 unhealthy"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$PA5_CT" ] || fail "running exe"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/w3_pa5.json" pa5 >> "$PROG" 2>&1 || fail "pa5 1"
date +%s%N > "$OLD/salt"
python3 "$W/ab_w1039.py" "$W/w3_pa52.json" pa52 >> "$PROG" 2>&1 || fail "pa5 2"

log "=== restore b12180 ==="
docker stop -t 30 $C >/dev/null || fail "stop before restore"
cp -f "$W/cfg_window3.bak" "$CFG" || sudo -n cp -f "$W/cfg_window3.bak" "$CFG"
[ "$(md5sum "$CFG" | cut -d' ' -f1)" = "$WANT_CFG" ] || fail "config md5"
docker start $C >/dev/null || fail "start after restore"
wait_health 420 || fail "restored unhealthy"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "$BASE_CT" ] || fail "restored exe"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
trap - EXIT
