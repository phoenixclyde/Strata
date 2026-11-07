#!/bin/bash
# W1036 / A0 A/B window, v2.  One binary swap, two arms, verified restore.
#
# v1 (06:03) failed twice and took production down for ~2.5 min:
#   1) the config's `exe` was set to the HOST path (/home/albus/.../bin/...).  The container sees the pools
#      under /data, so the engine could not be exec'd and docker restarted it in a loop.
#   2) the trap ran `cp -f` to restore the config and the file came back unchanged while the script went on to
#      "measure" the production binary as if it were the candidate.  Restore is now checked by md5, retried
#      with sudo, and a mismatch aborts instead of continuing.
#   3) a trap on TERM now exits (v1's handler returned and the script resumed after a signal).
#
#   arm "ctl" = strata-0.1.57-001   (production, dp4a = the portable loop)
#   arm "a0"  = strata-0.1.57-pa0   (port-all, every OPT flag OFF => the only difference is the dp4a intrinsic)
set -u
W=/home/albus/strata166/tmp/w1036
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
CAND_SRC=/home/albus/strata166/build-port2/strata
CAND_HOST=$BIN/strata-0.1.57-pa0
CAND_CT=/data/bin/strata-0.1.57-pa0          # the path the CONTAINER must be told
ORIG_CT=/data/bin/strata-0.1.57-001
WANT_MD5=53ac61e0c663a6a46b7a5aa2e610bf43
PROG=$W/a0v2_progress.log
: > "$PROG"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

wait_health() {
  local t=$1
  while [ "$t" -gt 0 ]; do
    if curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"'; then
      log "health ok after $(( $1 - t ))s"; return 0
    fi
    sleep 3; t=$((t - 3))
  done
  return 1
}

set_exe() {   # $1 = container path of the engine
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
  log "RESTORE (rc=$rc)"
  [ -f "$W/cfg_a0v2.bak" ] || { log "FATAL: no config backup"; return 1; }
  cp -f "$W/cfg_a0v2.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_a0v2.bak" "$CFG"
  local now; now=$(md5sum "$CFG" | cut -d' ' -f1)
  if [ "$now" != "$WANT_MD5" ]; then
    log "RESTORE: md5 $now != $WANT_MD5, retrying with sudo"
    sudo -n cp -f "$W/cfg_a0v2.bak" "$CFG"
    now=$(md5sum "$CFG" | cut -d' ' -f1)
  fi
  [ "$now" = "$WANT_MD5" ] || log "FATAL: config md5 still $now"
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 300 || log "WARN: health did not come back after restore"
  log "restore done: cfg=$(md5sum "$CFG" | cut -d' ' -f1) state=$(docker inspect -f '{{.State.Status}}' $C)"
}
trap restore EXIT
trap 'log "signal"; restore; exit 130' INT TERM

# ---- 0 preconditions ---------------------------------------------------------
log "=== preconditions ==="
[ -f "$CAND_SRC" ] || fail "candidate missing"
[ -f "$W/ab_a0.py" ] || fail "ab_a0.py missing"
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q $WANT_MD5 || fail "config md5 changed"
cp -f "$CFG" "$W/cfg_a0v2.bak"
md5sum "$W/cfg_a0v2.bak" | grep -q $WANT_MD5 || fail "backup md5 mismatch"
grep -q "$ORIG_CT" "$CFG" || fail "production exe is not $ORIG_CT"
log "cand_src=$(md5sum "$CAND_SRC" | cut -d' ' -f1) size=$(stat -c%s "$CAND_SRC")"

# ---- 1 arm ctl ---------------------------------------------------------------
# one salt per window: both arms get the same text, a later window never re-uses this one's cache entries
date +%s%N > "$W/a0_salt"
log "salt=$(cat "$W/a0_salt")"
log "=== arm ctl (-001) ==="
python3 "$W/ab_a0.py" "$W/a0_ctl.json" ctl >> "$PROG" 2>&1 || fail "ctl measurement failed"

# ---- 2 install candidate (file first, then swap) -----------------------------
log "=== install candidate ==="
cp -f "$CAND_SRC" "$CAND_HOST.new" || fail "cp candidate"
chmod 755 "$CAND_HOST.new"
mv -f "$CAND_HOST.new" "$CAND_HOST" || fail "mv candidate"
docker stop -t 30 $C >/dev/null || fail "docker stop"
set_exe "$CAND_CT" >> "$PROG" 2>&1 || fail "config exe rewrite"
grep -q "$CAND_CT" "$CFG" || fail "config still points at $ORIG_CT"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "candidate did not become healthy"
grep -q "$CAND_CT" "$CFG" || fail "config changed under us"

# ---- 3 arm a0 ---------------------------------------------------------------
log "=== arm a0 (port-all, flags off) ==="
python3 "$W/ab_a0.py" "$W/a0_cand.json" a0 >> "$PROG" 2>&1 || fail "a0 measurement failed"

# ---- 4 restore ---------------------------------------------------------------
log "=== restore production ==="
docker stop -t 30 $C >/dev/null
cp -f "$W/cfg_a0v2.bak" "$CFG" || sudo -n cp -f "$W/cfg_a0v2.bak" "$CFG"
grep -q "$ORIG_CT" "$CFG" || fail "restore: config still points at the candidate"
docker start $C >/dev/null
wait_health 420 || fail "production did not come back"
log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1) engines=$(pgrep -c -x strata-host)"
