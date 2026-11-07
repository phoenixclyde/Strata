#!/bin/bash
# W1042: does the ported attention OPT (B1/B2) belong in production?  One window, three phases, nothing installed.
#
#  P1 numeric  (qq_r103.py, production-shaped config incl. --kv-grow)
#      A = kvg                 baseline (production)
#      B = attn, no switch     floor: MUST be byte-identical to A
#      C = attn + ATTN_DP4A=1  the candidate
#  P2 timing   (same exe `attn`, server on 8090 with --network host, harness on the host so the salt works)
#  P3 task     (16K / 28K needle, both arms must hit)
set -u
S=/home/albus/strata166
W=$S/tmp/w1042
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
SALT=$S/tmp/w1037/salt
WANT_CFG=ee69ebc272ce41a116f50ecb3bf0edc2
PROG=$W/window.log
mkdir -p "$W"
: > "$PROG"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }
wait_health() {
  local t0=$1 t=$1
  while [ "$t" -gt 0 ]; do
    curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"' && { log "health ok after $(( t0 - t ))s"; return 0; }
    sleep 3; t=$((t - 3))
  done
  return 1
}
restore() {
  local rc=$?
  docker rm -f qq12_A qq12_B qq12_C qq12_srv >/dev/null 2>&1
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then docker start $C >/dev/null 2>&1; fi
  wait_health 420 || log "WARN: health did not return"
  log "RESTORE (rc=$rc) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
md5sum "$CFG" | grep -q $WANT_CFG || fail "config changed"
md5sum "$S/data/bin/strata-0.1.57-attn" | grep -q 3b758f88ddad25cdad236be267810a9e || fail "attn candidate md5 mismatch"
md5sum "$S/data/bin/strata-0.1.57-kvg"  | grep -q a85743d7f554159e8ac1e2d432d2e5ea || fail "kvg md5 mismatch"
log "downtime starts now"
T0=$(date +%s)
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 2

# ---------------------------------------------------------------- P1 numeric
run_num() {  # $1 tag  $2 cfg  $3 extra qq arg
  log "=== P1 arm $1 ==="
  docker run --rm --name qq12_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 900 python3 /w/qq_r103.py prompt --config /w/$2 --out /w/n_$1 --ids /w/set20k.ids.json --gpu-experts $3" \
    >> "$PROG" 2>&1
  local rc=$?
  log "P1 $1 rc=$rc files=$(ls -1 $W/n_$1 2>/dev/null | wc -l)"
  docker rm -f qq12_$1 >/dev/null 2>&1
  return $rc
}
run_num A cfgP_kvg.json "" || fail "numeric A failed"
run_num B cfgP_attn.json "" || fail "numeric B failed"
run_num C cfgP_attn.json "--env STRATA_GFX906_ATTN_DP4A=1" || fail "numeric C failed"

log "=== P1 floor + target (bytes) ==="
RC=0
for i in 0 1 2 3; do
  if cmp -s "$W/n_A/first.$i" "$W/n_B/first.$i"; then log "floor[$i] IDENTICAL"; else log "floor[$i] DIFFERS"; RC=1; fi
done
for i in 0 1 2 3; do cmp -s "$W/n_A/first.$i" "$W/n_C/first.$i" && log "C[$i] identical" || log "C[$i] differs"; done
[ "$RC" = "0" ] || fail "FLOOR BROKEN: attn(no switch) != kvg -> the port is not behaviour-neutral, stop"

log "=== P1 prefill timings (same runs) ==="
python3 - "$W" <<'PY' 2>&1 | tee -a "$PROG"
import io, re, sys
W = sys.argv[1]
print("%-3s %7s %9s %8s %7s" % ("arm", "tokens", "GPU ms", "attn", "attn%"))
for t in ("A", "B", "C"):
    txt = io.open("%s/n_%s/stderr.txt" % (W, t), encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms.*?qsa attn (\d+) \(([\d.]+)%\)", txt, re.S):
        print("%-3s %7s %9s %8s %6s%%" % (t, m.group(1), m.group(2), m.group(3), m.group(4)))
PY

# ---------------------------------------------------------------- P2 + P3: a temp server on 8090 (host network)
srv_up() {   # $1 env-string (may be empty)
  docker rm -f qq12_srv >/dev/null 2>&1
  local E="NOOP=1"
  [ -n "$1" ] && E="$1"
  docker run -d --name qq12_srv --network host --device=/dev/kfd --device=/dev/dri \
    -e "$E" -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /w/cfgP_attn.json --port 8090" \
    >> "$PROG" 2>&1
  wait_health 480
}
srv_down() { docker rm -f qq12_srv >/dev/null 2>&1; sleep 3; }

log "=== P2 timing: off ==="
: > "$W/srv.log"; srv_up "" || fail "temp server (off) did not come up"
date +%s%N > "$SALT"
W1042_LOG="$W/srv.log" python3 "$W/ab_w1042.py" "$W/t_T1.json" T1 >> "$PROG" 2>&1; log "P2 T1 rc=$?"
srv_down

log "=== P2 timing: DP4A on ==="
: > "$W/srv.log"; srv_up "STRATA_GFX906_ATTN_DP4A=1" || fail "temp server (on) did not come up"
date +%s%N > "$SALT"
W1042_LOG="$W/srv.log" python3 "$W/ab_w1042.py" "$W/t_T2.json" T2 >> "$PROG" 2>&1; log "P2 T2 rc=$?"
srv_down

log "=== P3 needle: off ==="
srv_up "" || fail "needle server (off) did not come up"
python3 "$W/needle1042.py" S1 >> "$PROG" 2>&1; log "P3 S1 rc=$?"
srv_down

log "=== P3 needle: DP4A on ==="
srv_up "STRATA_GFX906_ATTN_DP4A=1" || fail "needle server (on) did not come up"
python3 "$W/needle1042.py" S2 >> "$PROG" 2>&1; log "P3 S2 rc=$?"
srv_down

log "=== start production back ==="
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "production did not come back"
T1=$(date +%s)
log "DONE exe=$(pgrep -a -x strata-host | awk '{print $2}') downtime=$(( T1 - T0 ))s"
trap - EXIT
