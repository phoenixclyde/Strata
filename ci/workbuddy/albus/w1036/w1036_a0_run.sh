#!/bin/bash
# W1036 / A0 A/B window.  One binary swap, two arms, automatic restore.
#
#   arm "ctl"  = the production binary strata-0.1.57-001 (dp4a = the portable loop)
#   arm "a0"   = the port-all binary, every OPT flag OFF (so the only difference is the dp4a intrinsic)
#
# Stop time: stop(10 s) + start(~50 s) + measure(~90 s) + stop/start + measure(~90 s) + restore start(~50 s)
# ~ 5 min.  The script restores the production config and binary on ANY exit path.
set -u
W=/home/albus/strata166/tmp/w1036
DATA=/home/albus/strata166/data
BIN=$DATA/bin
CFG=$DATA/strata-huihui-ud-iq4_xs.json
C=strata166-407
CAND_SRC=/home/albus/strata166/build-port2/strata
CAND=$BIN/strata-0.1.57-pa0
PROG=$W/a0_progress.log
: > "$PROG"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

wait_health() {          # $1 = seconds
  local t=$1
  while [ "$t" -gt 0 ]; do
    if curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"'; then
      log "health ok after $(( $1 - t ))s"
      return 0
    fi
    sleep 3; t=$((t - 3))
  done
  return 1
}

restore() {
  local rc=$?
  log "RESTORE (exit rc=$rc)"
  [ -f "$W/cfg_a0.json.bak" ] && cp -f "$W/cfg_a0.json.bak" "$CFG"
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 300 || log "WARN: health did not come back after restore"
  log "restored cfg md5=$(md5sum "$CFG" | cut -d' ' -f1) (want 53ac61e0c663a6a46b7a5aa2e610bf43)"
}
trap restore EXIT INT TERM

# ---- 0 preconditions ---------------------------------------------------------
log "=== preconditions ==="
[ -f "$CAND_SRC" ] || fail "candidate binary missing: $CAND_SRC"
[ -f "$W/ab_a0.py" ] || fail "ab_a0.py missing"
N=$(pgrep -c -x strata-host 2>/dev/null || echo 0)   # exact comm: a pgrep -f pattern matches its own shell
[ "$N" = "1" ] || fail "expected exactly 1 engine process, found $N"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q 53ac61e0c663a6a46b7a5aa2e610bf43 || fail "config md5 changed"
cp -f "$CFG" "$W/cfg_a0.json.bak"
log "cand=$(md5sum "$CAND_SRC" | cut -d' ' -f1) size=$(stat -c%s "$CAND_SRC")"

# ---- 1 arm ctl (production binary already running) ---------------------------
log "=== arm ctl (-001, production) ==="
python3 "$W/ab_a0.py" "$W/a0_ctl.json" ctl >> "$PROG" 2>&1 || fail "ctl measurement failed"

# ---- 2 install candidate ----------------------------------------------------
log "=== install candidate (cp -> .new, mv) ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
cp -f "$CAND_SRC" "$CAND.new" || fail "cp candidate"
chmod 755 "$CAND.new"
mv -f "$CAND.new" "$CAND" || fail "mv candidate"
python3 - "$CFG" "$CAND" <<'PY' || fail "config exe rewrite"
import io, json, sys
p, exe = sys.argv[1], sys.argv[2]
d = json.load(io.open(p, encoding="utf-8-sig"))
d["exe"] = exe
io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(d, ensure_ascii=False, indent=1))
print("exe ->", exe)
PY
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "candidate did not become healthy"

# ---- 3 arm a0 ---------------------------------------------------------------
log "=== arm a0 (port-all, all OPT flags off => dp4a only) ==="
python3 "$W/ab_a0.py" "$W/a0_cand.json" a0 >> "$PROG" 2>&1 || fail "a0 measurement failed"

# ---- 4 restore (also runs from the trap) ------------------------------------
log "=== restore production ==="
docker stop -t 30 $C >/dev/null
cp -f "$W/cfg_a0.json.bak" "$CFG"
docker start $C >/dev/null
wait_health 420 || fail "production did not come back"
log "DONE cfg_md5=$(md5sum "$CFG" | cut -d' ' -f1) engines=$(pgrep -c -x strata-host)"
