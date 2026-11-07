#!/bin/bash
# W1040 / R104 install window.
#
#  0. preconditions: production b12180 (d24f8293) + config 5e9b81e2, health ok, candidate kvg (a85743d7) present
#  1. STOP production (downtime starts) - the GPU must be free for the two numeric arms
#  2. D4 numeric: the same batched prompt path, full-vocabulary fp32 logits after 1000 / 8000 / 16000 / 20000 tokens
#       arm A = b12180                 (baseline; kv-grow impossible without VMM)
#       arm B = kvg + --kv-grow        (candidate)
#     1000/8000/16000 are all <= STRATA_KV_GROW_INIT (16384 cells) => no growth, no expert evicted,
#     so those three MUST be byte-identical.  20000 forces one growth; the growth borrows slots from the
#     expert cache by design, so that one is reported as KL/top-1, not as identity.
#  3. install: config 5e9b81e2 -> ee69ebc2 (exe + --kv-grow only), start, health, read the NEW log slice
#  4. rollback: any failure after the stop restores cfg_w1040.bak and starts b12180 again
set -u
S=/home/albus/strata166
W=$S/tmp/w1040
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$S/data/strata-huihui-ud-iq4_xs.log
NEW=/data/bin/strata-0.1.57-kvg
WANT_NEW=a85743d7f554159e8ac1e2d432d2e5ea
WANT_CFG=5e9b81e2f66ca48999766d2ae0201fb6
WANT_NEWCFG=ee69ebc272ce41a116f50ecb3bf0edc2
PROG=$W/install.log
mkdir -p "$W"
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

restore() {
  local rc=$?
  docker rm -f qq10_A qq10_B >/dev/null 2>&1
  if [ -f "$W/cfg_w1040.bak" ] && [ "$(md5sum "$CFG" 2>/dev/null | cut -d' ' -f1)" != "$WANT_CFG" ]; then
    cp -f "$W/cfg_w1040.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_w1040.bak" "$CFG"
    log "config rolled back to $(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12)"
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 420 || log "WARN: health did not return during restore"
  log "RESTORE (rc=$rc) cfg=$(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected exactly 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$S/data/bin/strata-0.1.57-kvg" | grep -q $WANT_NEW || fail "candidate md5 mismatch"
md5sum "$CFG" | grep -q $WANT_CFG || fail "config md5 is not $WANT_CFG"
[ -f "$W/cfg_new.json" ] || fail "cfg_new.json missing"
md5sum "$W/cfg_new.json" | grep -q $WANT_NEWCFG || fail "cfg_new.json md5 is not $WANT_NEWCFG"
cp -f "$CFG" "$W/cfg_w1040.bak"
log "preconditions ok; downtime starts now"

log "=== stop production ==="
T0=$(date +%s)
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 2
[ "$(pgrep -c -x strata-host)" = "0" ] || fail "engine still alive"

run_arm() {   # $1 tag  $2 cfg
  log "=== arm $1 ($2) ==="
  docker run --rm --name qq10_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 900 python3 /w/qq_prompt.py prompt --config /w/$2 --out /w/pa_$1 --ids /w/set20k.ids.json --gpu-experts" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc  files=$(ls -1 $W/pa_$1 2>/dev/null | wc -l)"
  docker rm -f qq10_$1 >/dev/null 2>&1
  return $rc
}

run_arm A cfg_armA.json || fail "arm A failed"
grep -a "expert cache [0-9]* slots" $W/pa_A/stderr.txt | tail -1 | tee -a "$PROG" || true
grep -a "elastic K/V" $W/pa_A/stderr.txt | tail -1 | tee -a "$PROG" || log "arm A: no elastic line (expected: kv-grow is off)"

run_arm B cfg_armB.json || fail "arm B failed"
grep -a "expert cache [0-9]* slots" $W/pa_B/stderr.txt | tail -1 | tee -a "$PROG" || true
if ! grep -aq "elastic K/V" $W/pa_B/stderr.txt; then
  fail "arm B never printed the elastic K/V line => kv-grow was NOT on; the comparison would be meaningless"
fi
grep -a "elastic K/V" $W/pa_B/stderr.txt | tail -1 | tee -a "$PROG"
log "--- arm B failure lines (want none) ---"
grep -aE "could not map|ERR the K/V could not|out of VRAM" $W/pa_B/stderr.txt | tail -5 | tee -a "$PROG" || log "(none)"

log "=== D4 compare: fp32 logits, byte identity where no growth can happen ==="
RC=0
for i in 0 1 2; do
  if cmp -s "$W/pa_A/first.$i" "$W/pa_B/first.$i"; then
    log "first.$i  IDENTICAL  $(md5sum "$W/pa_A/first.$i" | cut -d' ' -f1)  ($(stat -c%s "$W/pa_A/first.$i") B)"
  else
    log "first.$i  DIFFERS  A=$(md5sum "$W/pa_A/first.$i" | cut -d' ' -f1)  B=$(md5sum "$W/pa_B/first.$i" | cut -d' ' -f1)"
    RC=1
  fi
done
if cmp -s "$W/pa_A/first.3" "$W/pa_B/first.3"; then
  log "first.3  IDENTICAL (growth path also bit-identical)"
else
  log "first.3  differs (growth path: expected, slots are borrowed from the expert cache)"
fi
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && python3 /w/qq_prompt.py pcompare /w/pa_A /w/pa_B" >> "$PROG" 2>&1
grep -a "prompts" "$PROG" | tail -2
[ "$RC" = "0" ] || fail "D4 not bit-identical on the no-growth range: nothing installed, production untouched"

log "=== install: config 5e9b81e2 -> $WANT_NEWCFG ==="
BEFORE=$(wc -l < "$LOG")
cp -f "$W/cfg_new.json" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_new.json" "$CFG"
NOW=$(md5sum "$CFG" | cut -d' ' -f1)
[ "$NOW" = "$WANT_NEWCFG" ] || fail "config md5 after push is $NOW"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "kvg did not become healthy"
T1=$(date +%s)
RUN=$(pgrep -a -x strata-host | awk '{print $2}')
log "running: $RUN  (downtime $(( T1 - T0 )) s)"
[ "$(docker exec $C md5sum $NEW | cut -d' ' -f1)" = "$WANT_NEW" ] || fail "running binary is not $NEW"

log "=== post-install: the NEW log slice only (line $BEFORE onwards) ==="
tail -n +$((BEFORE + 1)) "$LOG" > "$W/new_start.log"
grep -a "expert cache [0-9]* slots" "$W/new_start.log" | tail -2 | tee -a "$PROG" || true
grep -a "elastic K/V" "$W/new_start.log" | tail -1 | tee -a "$PROG" || true
if grep -aq -- "--kv-grow is off" "$W/new_start.log"; then log "!! engine says kv-grow is OFF"; else log "(no 'kv-grow is off' line: correct)"; fi
grep -aE "could not map|ERR the K/V could not" "$W/new_start.log" | tail -3 | tee -a "$PROG" || log "(no failure lines: correct)"

grep -aq "expert cache 8301 slots" "$W/new_start.log" || fail "installed engine did not report 8301 slots"
grep -aq "elastic K/V: 16384 of 262144 cells" "$W/new_start.log" || fail "installed engine did not report the elastic K/V"
if grep -aq -- "--kv-grow is off" "$W/new_start.log"; then fail "engine says kv-grow is OFF"; fi
if grep -aq "could not map" "$W/new_start.log"; then fail "map failure in the new run"; fi

log "DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1) exe=$(pgrep -a -x strata-host | awk '{print $2}') downtime=$(( T1 - T0 ))s"
trap - EXIT
