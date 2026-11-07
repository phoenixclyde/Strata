#!/bin/bash
# W1041b: arm D only (the -11.3% arm and the build-floor arm are already on disk).
# D failed on `--kv f16`: the engine says `--kv must be fp16, int8, q4_0 or k8v4`.
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
C=strata166-407
LOGPROG=$W/window_d.log
: > "$LOGPROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOGPROG"; }
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
  docker rm -f qq11_D >/dev/null 2>&1
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 420 || log "WARN: health did not return during restore"
  log "RESTORE (rc=$rc) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
log "downtime starts now"
T0=$(date +%s)
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 2

log "=== arm D (b12180, --kv fp16) ==="
docker run --rm --name qq11_D --device=/dev/kfd --device=/dev/dri -e QQ_KV=fp16 \
  -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
  bash -lc "timeout 900 python3 /w/qq_r103.py prompt --config /w/cfgD.json --out /w/lg_D --ids /w/set20k.ids.json --gpu-experts" \
  >> "$LOGPROG" 2>&1
RC=$?
log "arm D rc=$RC files=$(ls -1 $W/lg_D 2>/dev/null | wc -l)"
docker rm -f qq11_D >/dev/null 2>&1
[ "$RC" = "0" ] || { tail -5 "$W/lg_D/stderr.txt" | tee -a "$LOGPROG"; }

log "=== exact byte comparison vs A ==="
for i in 0 1 2 3; do
  if cmp -s "$W/lg_A/first.$i" "$W/lg_D/first.$i"; then log "D[$i] IDENTICAL"; else log "D[$i] differs"; fi
done
log "--- arm D prefill timing ---"
grep -a "strata prefill timing:" "$W/lg_D/stderr.txt" | tail -4 | sed 's/strata prefill timing: //' | cut -c1-200 | tee -a "$LOGPROG"

log "=== start production back ==="
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "production did not come back"
T1=$(date +%s)
log "DONE exe=$(pgrep -a -x strata-host | awk '{print $2}') downtime=$(( T1 - T0 ))s"
trap - EXIT
