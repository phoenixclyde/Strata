#!/bin/bash
# W1043 / R103 install window -- **NOT EXECUTED, WAITING FOR EXPLICIT DOWNTIME APPROVAL**.
# Spec (pre-registered, do not change the criteria after the run): albus/w1043/LONGCTX_GATE.md
#
# This script is FAIL-CLOSED: it refuses to stop production unless BOTH
#   APPROVED=1  and  DRY_RUN=0
# are passed explicitly.  A bare `bash window_install_attn.sh` only prints the plan.
#
# Order (one window, one stop/start):
#   0 preconditions: production kvg (a85743d7) + config ee69ebc2, health ok,
#                    candidate attn (3b758f88) present, register row for the switch ADOPTED
#   1 STOP production  <-- downtime starts
#   2 G1 combo re-verification (A=kvg vs B=attn no switch, BOTH with --kv-grow)
#   3 G2/G3 logits: D anchor + 32K/64K points   [PREP: qq_r103.py ids sets set32k/set64k first]
#   4 G4 needle grid: off / on, 16K/32K/64K x 0/50/100%  (longctx_needle.py)
#   5 judge -> verdict.json; ONLY if G1..G5 all pass -> install
#   6 install: exe -> attn, env +STRATA_GFX906_ATTN_DP4A=1, restart, health, NEW log slice
#   7 trap: ANY failure restores kvg + ee69ebc2 and starts production
set -u
APPROVED=${APPROVED:-0}
DRY_RUN=${DRY_RUN:-1}
S=/home/albus/strata166
W=$S/tmp/w1043
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$S/data/strata-huihui-ud-iq4_xs.log
WANT_OLD=a85743d7f554159e8ac1e2d432d2e5ea
WANT_NEW=3b758f88ddad25cdad236be267810a9e
WANT_CFG=ee69ebc272ce41a116f50ecb3bf0edc2
PROG=$W/window.log

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

if [ "$APPROVED" != 1 ] || [ "$DRY_RUN" != 0 ]; then
  echo "DRY RUN (APPROVED=$APPROVED DRY_RUN=$DRY_RUN): no production change."
  echo "  estimated downtime 20-30 min (EXTRAPOLATED from W1042 28K needle = 39.0 s; NOT measured)"
  echo "  to actually run:  APPROVED=1 DRY_RUN=0 bash window_install_attn.sh"
  exit 0
fi

mkdir -p "$W"; : > "$PROG"
log "=== W1043 install window; spec LONGCTX_GATE.md; APPROVED=1 ==="

wait_health() {
  local t0=$1 t=$1
  while [ "$t" -gt 0 ]; do
    curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"' \
      && { log "health ok after $((t0 - t))s"; return 0; }
    sleep 3; t=$((t - 3))
  done
  return 1
}
restore() {
  local rc=$?
  docker rm -f q43_A q43_B q43_D q43_srv >/dev/null 2>&1
  if [ -f "$W/cfg_w1043.bak" ]; then
    cp -f "$W/cfg_w1043.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_w1043.bak" "$CFG"
    log "config restored to $(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12)"
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 420 || log "WARN: health did not return during restore"
  log "RESTORE (rc=$rc) cfg=$(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions (fail-closed) ==="
[ "$(pgrep -c -x strata-host)" = 1 ] || fail "expected exactly 1 engine process"
docker inspect -f '{{.State.Running}}' $C | grep -q true || fail "container not running"
curl -s -m 10 localhost:8090/health | grep -qE '"status": *"ok"' || fail "health not ok"
md5sum "$CFG" | grep -q "$WANT_CFG" || fail "production config is not $WANT_CFG"
md5sum "$S/data/bin/strata-0.1.57-kvg"  | grep -q "$WANT_OLD" || fail "rollback engine md5 mismatch"
md5sum "$S/data/bin/strata-0.1.57-attn" | grep -q "$WANT_NEW" || fail "candidate md5 mismatch"
[ -f "$W/cfg_new.json" ] || fail "cfg_new.json missing (register row + gen_config bridge first)"
[ -f "$W/set32k.ids.json" ] && [ -f "$W/set64k.ids.json" ] || fail "32K/64K ids sets not built (qq_r103.py ids)"
grep -q "STRATA_GFX906_ATTN_DP4A" "$S/deploy/params/PARAM_REGISTER.tsv" \
  || fail "switch not ADOPTED in register -> D5 would REFUSE"
cp -f "$CFG" "$W/cfg_w1043.bak"
LOGLINES=$(wc -l < "$LOG")      # P493: never grep the whole append-only log
log "preconditions ok; LOGLINES=$LOGLINES; DOWNTIME STARTS NOW"
T0=$(date +%s)
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 2
[ "$(pgrep -c -x strata-host)" = 0 ] || fail "engine still alive"

# ---- G1: combo build floor (both arms carry --kv-grow, verified W1043/P510)
run_num() {  # $1 tag  $2 cfg  $3 extra qq arg
  log "=== G1 arm $1 ==="
  docker run --rm --name q43_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 900 python3 /w/qq_r103.py prompt --config /w/$2 --out /w/g_$1 \
              --ids /w/set20k.ids.json --gpu-experts $3" >> "$PROG" 2>&1
  return $?
}
run_num A cfgP_kvg.json  "" || fail "G1 A failed"
run_num B cfgP_attn.json "" || fail "G1 B failed"
for i in 0 1 2 3; do
  cmp -s "$W/g_A/first.$i" "$W/g_B/first.$i" || fail "G1 FLOOR BROKEN at point $i"
done
log "G1 PASS (4/4 byte-identical)"

# ---- G2/G3: D anchor + 32K/64K logits (same qq_r103 yardstick, different ids sets)
#   D = kvg + --kv fp16 : run_num D cfgP_kvg.json "--env QQ_KV=fp16"
#   then cmp_logits.py over A/C/D for 1K..64K -> KL(C)/KL(D) ratio; G3 = ratio@64K <= 2*ratio@20K
log "TODO-BEFORE-RUN: wire G2/G3 logits here; DO NOT install without verdict.json G2/G3"

# ---- G4: needle grid, two arms (temp server, host network)
srv_up() {
  docker rm -f q43_srv >/dev/null 2>&1
  local E=""; [ -n "${1:-}" ] && E="$1"
  docker run -d --name q43_srv --network host --device=/dev/kfd --device=/dev/dri \
    -e "$E" -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /w/cfgP_attn.json --port 8090" \
    >> "$PROG" 2>&1
  wait_health 480
}
srv_down() { docker rm -f q43_srv >/dev/null 2>&1; sleep 3; }
log "=== G4 needle grid: off ==="
srv_up "" || fail "temp server (off) did not come up"
python3 "$W/longctx_needle.py" --label off --out "$W/grid_off.json" >> "$PROG" 2>&1 || fail "needle off failed"
srv_down
log "=== G4 needle grid: on ==="
srv_up "STRATA_GFX906_ATTN_DP4A=1" || fail "temp server (on) did not come up"
python3 "$W/longctx_needle.py" --label on --out "$W/grid_on.json" >> "$PROG" 2>&1 || fail "needle on failed"
srv_down

# ---- verdict (G1..G5). judge.py must be written BEFORE this window is approved.
[ -f "$W/verdict.json" ] || fail "verdict.json missing -- G2/G3/G5 not judged, refusing to install"
python3 - "$W/verdict.json" <<'PY' || fail "verdict says NO-GO"
import json,sys
v=json.load(open(sys.argv[1]))
need=["G1","G2","G3","G4","G5"]
print("VERDICT", {k:v.get(k) for k in need})
raise SystemExit(0 if all(v.get(k) is True for k in need) else 1)
PY

# ---- install (only reached when the gate passed)
log "=== install attn ==="
cp -f "$W/cfg_new.json" "$CFG" || fail "cannot write config"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "health did not return after install"
NEW=$(pgrep -a -x strata-host | awk '{print $2}')
[ "$NEW" = "/data/bin/strata-0.1.57-attn" ] || fail "running engine is $NEW, not attn"
tail -n +$((LOGLINES+1)) "$LOG" > "$W/new_start.log"     # P493: slice only the new lines
grep -q "expert cache 8301 slots" "$W/new_start.log" || log "WARN: no 8301-slot line in new slice"
grep -q "kv-grow is off" "$W/new_start.log" && fail "kv-grow is OFF in the new slice"
T1=$(date +%s)
log "DONE installed exe=$NEW cfg=$(md5sum "$CFG" | cut -d' ' -f1) downtime=$((T1-T0))s"
trap - EXIT
