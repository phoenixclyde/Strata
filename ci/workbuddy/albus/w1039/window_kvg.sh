#!/bin/bash
# W1039 / R104: the --kv-grow window.  Two restarts (install, restore), ~45 s each.
#
# Arm A = production b12180 as it stands (no restart).
# Arm B = the same tree with the VMM guard lifted for gfx906 (strata-0.1.57-kvg, a85743d7) + STRATA_KV_GROW=1.
# What is read out of arm B's start-up: the "elastic K/V: N of M cells in VRAM (... GiB)" line and the expert
# cache slot count - that pair IS the win (slots bought by not reserving 2.2 GiB of K/V).
set -u
W=/home/albus/strata166/tmp/w1039
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=$DATA/strata-huihui-ud-iq4_xs.log
C=strata166-407
NEW_CT=/data/bin/strata-0.1.57-kvg
CUR_CT=/data/bin/strata-0.1.57-b12180
WANT_CUR=d24f8293b575fbcee6c097239d9599cb
WANT_NEW=a85743d7f554159e8ac1e2d432d2e5ea
WANT_CFG=5e9b81e2f66ca48999766d2ae0201fb6
PROG=$W/kvg.log
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

set_exe_env() {   # $1 = container exe path, $2 = 1 to add STRATA_KV_GROW
  python3 - "$CFG" "$1" "$2" <<'PY' || return 1
import io, json, sys
p, exe, grow = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
env = d.get("env") or {}
if grow == "1":
    env["STRATA_KV_GROW"] = "1"
else:
    env.pop("STRATA_KV_GROW", None)
d["env"] = env
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("exe ->", exe, "| STRATA_KV_GROW =", env.get("STRATA_KV_GROW"))
PY
}

startup_notes() {   # what the elastic K/V and the cache say at load time
  log "--- startup lines ---"
  grep -aE "elastic K/V|expert cache [0-9]+ slots|kv-grow is off|expert cache: [0-9]+" "$LOG" | tail -6 | tee -a "$PROG"
}

restore() {
  local rc=$?
  if [ -f "$W/cfg_kvg.bak" ]; then
    cp -f "$W/cfg_kvg.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_kvg.bak" "$CFG"
    local now; now=$(md5sum "$CFG" | cut -d' ' -f1)
    [ "$now" = "$WANT_CFG" ] || { sudo -n cp -f "$W/cfg_kvg.bak" "$CFG"; now=$(md5sum "$CFG" | cut -d' ' -f1); }
    log "RESTORE (rc=$rc) cfg=$(echo $now | cut -c1-12)"
    [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" = "true" ] || docker start $C >/dev/null 2>&1
    wait_health 420 || log "WARN: health did not return after restore"
  fi
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ -f "$BIN/strata-0.1.57-kvg" ] || fail "candidate missing"
md5sum "$BIN/strata-0.1.57-kvg" | grep -q $WANT_NEW || fail "candidate md5 mismatch"
md5sum "$BIN/strata-0.1.57-b12180" | grep -q $WANT_CUR || fail "rollback md5 mismatch"
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected exactly 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q $WANT_CFG || fail "config md5 changed before we started"
grep -q "$CUR_CT" "$CFG" || fail "production exe is not $CUR_CT"
cp -f "$CFG" "$W/cfg_kvg.bak"
log "candidate ok: $(md5sum "$BIN/strata-0.1.57-kvg" | cut -c1-12) $(stat -c%s "$BIN/strata-0.1.57-kvg") B"

date +%s%N > "$W/salt"
log "=== arm A (in place: b12180, no restart) ==="
python3 "$W/ab_kvg.py" "$W/arm_kvgA.json" A >> "$PROG" 2>&1 || fail "arm A failed"
date +%s%N > "$W/salt"
log "=== arm A pass 2 (same arm, fresh salt: n=4 per target) ==="
python3 "$W/ab_kvg.py" "$W/arm_kvgA2.json" A2 >> "$PROG" 2>&1 || fail "arm A pass 2 failed"
log "--- arm A decode breakdown (the CPU-expert segment is R104's second endpoint, P482) ---"
grep -a "strata decode timing:" "$LOG" | tail -1 | tee -a "$PROG"

log "=== swap to kvg + STRATA_KV_GROW=1 ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
set_exe_env "$NEW_CT" 1 >> "$PROG" 2>&1 || fail "config rewrite"
grep -q "$NEW_CT" "$CFG" || fail "config still points at $CUR_CT"
grep -q STRATA_KV_GROW "$CFG" || fail "STRATA_KV_GROW not in config"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "kvg did not become healthy"
RUN=$(pgrep -a -x strata-host | awk '{print $2}')
log "running: $RUN"
[ "$RUN" = "$NEW_CT" ] || fail "running exe is $RUN, not $NEW_CT"
startup_notes

date +%s%N > "$W/salt"
log "=== arm B (kvg, kv-grow on) ==="
python3 "$W/ab_kvg.py" "$W/arm_kvgB.json" B >> "$PROG" 2>&1 || fail "arm B failed"
date +%s%N > "$W/salt"
log "=== arm B pass 2 ==="
python3 "$W/ab_kvg.py" "$W/arm_kvgB2.json" B2 >> "$PROG" 2>&1 || fail "arm B pass 2 failed"
log "=== verdict ==="
python3 "$W/summarize_kvg.py" "$W/arm_kvgA.json" "$W/arm_kvgA2.json" -- "$W/arm_kvgB.json" "$W/arm_kvgB2.json" >> "$PROG" 2>&1 || log "WARN summarize failed"
tail -20 "$PROG"
log "--- arm B decode breakdown ---"
grep -a "strata decode timing:" "$LOG" | tail -1 | tee -a "$PROG"

log "--- growth / failure lines after arm B ---"
grep -aE "elastic K/V|could not map|no VRAM left" "$LOG" | tail -8 | tee -a "$PROG"

log "=== restore b12180 ==="
docker stop -t 30 $C >/dev/null || fail "docker stop (restore)"
cp -f "$W/cfg_kvg.bak" "$CFG" || fail "config restore"
md5sum "$CFG" | grep -q $WANT_CFG || fail "config md5 is not back to $WANT_CFG"
docker start $C >/dev/null || fail "docker start (restore)"
wait_health 420 || fail "production did not come back"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
trap - EXIT
