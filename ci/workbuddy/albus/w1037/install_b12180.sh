#!/bin/bash
# W1037: install llama.cpp b12180 (== master bcb01528) + mmq@4c1004c into production.
# One restart. Rollback = the current production engine (k10p). Automatic on health/identity failure;
# performance is judged by the numbers afterwards (arm JSON is written either way).
set -u
W=/home/albus/strata166/tmp/w1037
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
NEW_CT=/data/bin/strata-0.1.57-b12180
OLD_CT=/data/bin/strata-0.1.57-k10p
WANT_OLD=e23bbce525487636eeac7020960c46c6
WANT_NEW=d24f8293b575fbcee6c097239d9599cb
PROG=$W/install12180.log
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

set_exe() {
  python3 - "$CFG" "$1" <<'PY' || return 1
import io, json, sys
p, exe = sys.argv[1], sys.argv[2]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("exe ->", exe)
PY
}

restore() {
  local rc=$?
  if [ -f "$W/cfg_12180.bak" ]; then
    cp -f "$W/cfg_12180.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_12180.bak" "$CFG"
    local now; now=$(md5sum "$CFG" | cut -d' ' -f1)
    [ "$now" = "$WANT_OLD" ] || { sudo -n cp -f "$W/cfg_12180.bak" "$CFG"; now=$(md5sum "$CFG" | cut -d' ' -f1); }
    log "RESTORE (rc=$rc) cfg=$(echo $now | cut -c1-12)"
    [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" = "true" ] || docker start $C >/dev/null 2>&1
    wait_health 420 || log "WARN: health did not return after restore"
  fi
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ -f "$BIN/strata-0.1.57-b12180" ] || fail "candidate missing"
md5sum "$BIN/strata-0.1.57-b12180" | grep -q $WANT_NEW || fail "candidate md5 mismatch"
md5sum "$BIN/strata-0.1.57-k10p"   | grep -q e0a6987f732a401f780f5dad5812812f || fail "rollback k10p md5 mismatch"
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected exactly 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q $WANT_OLD || fail "config md5 changed before we started"
grep -q "$OLD_CT" "$CFG" || fail "production exe is not $OLD_CT"
cp -f "$CFG" "$W/cfg_12180.bak"
log "candidate ok: $(md5sum "$BIN/strata-0.1.57-b12180" | cut -c1-12) $(stat -c%s "$BIN/strata-0.1.57-b12180") B"

date +%s%N > "$W/salt"
log "=== swap to b12180 ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
set_exe "$NEW_CT" >> "$PROG" 2>&1 || fail "config rewrite"
grep -q "$NEW_CT" "$CFG" || fail "config still points at $OLD_CT"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "b12180 did not become healthy"

RUN=$(pgrep -a -x strata-host | awk '{print $2}')
log "running: $RUN"
[ "$RUN" = "$NEW_CT" ] || fail "running exe is $RUN, not $NEW_CT"

log "=== arm b12180 (1/2) ==="
python3 "$W/ab_w1037.py" "$W/arm_b12180.json" b12180 >> "$PROG" 2>&1 || fail "measurement 1 failed"
date +%s%N > "$W/salt"
log "=== arm b12180 (2/2) ==="
python3 "$W/ab_w1037.py" "$W/arm_b12180b.json" b12180b >> "$PROG" 2>&1 || fail "measurement 2 failed"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1) exe=$RUN"
trap - EXIT
