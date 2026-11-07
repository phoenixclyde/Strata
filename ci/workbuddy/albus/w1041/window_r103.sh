#!/bin/bash
# W1041 / R103 重开.  Four numeric arms, one stop/start, NOTHING is installed.
#
#   A = b12180, k8v4                     baseline
#   B = pa5,   k8v4, no switch           build floor (must be byte-identical to A)
#   C = pa5,   k8v4, ATTN_DP4A=1         the -11.3% attn arm
#   D = b12180, KV f16                   the anchor: what k8v4 already costs us
#
# Downtime = the four arms only (production is stopped for the GPU, then started again with the
# same exe/config it had: no install, no config change).
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
WANT_CFG=ee69ebc272ce41a116f50ecb3bf0edc2
PROG=$W/window.log
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
  docker rm -f qq11_A qq11_B qq11_C qq11_D >/dev/null 2>&1
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
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q $WANT_CFG || fail "config md5 changed before we started"
md5sum "$S/data/bin/strata-0.1.57-pa5" | grep -q c639b60c5981267c8d82ee3a4b0750e8 || fail "pa5 md5 mismatch"
log "preconditions ok; downtime starts now"

log "=== stop production ==="
T0=$(date +%s)
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 2
[ "$(pgrep -c -x strata-host)" = "0" ] || fail "engine still alive"

run_arm() {   # $1 tag  $2 cfg  $3 extra qq env (may be empty)  $4 docker -e (may be empty)
  log "=== arm $1 ==="
  docker run --rm --name qq11_$1 --device=/dev/kfd --device=/dev/dri \
    $4 -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 900 python3 /w/qq_r103.py prompt --config /w/$2 --out /w/lg_$1 --ids /w/set20k.ids.json --gpu-experts $3" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc files=$(ls -1 $W/lg_$1 2>/dev/null | wc -l)"
  docker rm -f qq11_$1 >/dev/null 2>&1
  return $rc
}

run_arm A cfgA.json ""                        ""                 || fail "arm A failed"
run_arm B cfgB.json ""                        ""                 || fail "arm B failed"
run_arm C cfgC.json "--env STRATA_GFX906_ATTN_DP4A=1" ""         || fail "arm C failed"
run_arm D cfgD.json ""                        "-e QQ_KV=f16"     || fail "arm D failed"

log "=== engine args actually used ==="
for t in A B C D; do
  python3 -c "import json;d=json.load(open('$W/lg_$t/index.json'));a=d['args'];print('$t','kv=',a[a.index('--kv')+1],'exe=',a[0].split('/')[-1],'env=',d.get('env'))" | tee -a "$PROG"
done

log "=== exact byte comparison ==="
for t in B C D; do
  for i in 0 1 2 3; do
    if cmp -s "$W/lg_A/first.$i" "$W/lg_$t/first.$i"; then
      log "$t[$i] IDENTICAL"
    else
      log "$t[$i] differs"
    fi
  done
done

log "=== prefill timings (the same runs, free) ==="
for t in A B C D; do
  log "--- arm $t ---"
  grep -a "strata prefill timing:" "$W/lg_$t/stderr.txt" | tail -4 | sed 's/strata prefill timing: //' | cut -c1-220 | tee -a "$PROG"
done

log "=== start production back (same exe/config as before) ==="
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "production did not come back"
T1=$(date +%s)
log "DONE exe=$(pgrep -a -x strata-host | awk '{print $2}') cfg=$(md5sum "$CFG" | cut -d' ' -f1) downtime=$(( T1 - T0 ))s"
trap - EXIT
