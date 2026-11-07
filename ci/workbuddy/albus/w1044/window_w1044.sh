#!/bin/bash
# W1044 / R103 INSTALL WINDOW -- approved by the owner at 17:01 ("装吧").
# Spec (pre-registered BEFORE this run): albus/w1043/LONGCTX_GATE.md, revised W1044 17:0x.
#
# One stop/start. Four arms share qq_long.py + set32k.ids.json (1K/8K/20K/32K):
#   A = kvg                      reference
#   B = attn, no switch          G1 build floor: byte-identical to A
#   C = attn + ATTN_DP4A=1       candidate
#   D = kvg + QQ_KV=fp16         anchor (must be an OUTER docker env, not --env)
# Then G4 needle grid (16K/32K/64K x 0/50/100% x off/on), G5 pre-set timing,
# judge.py G1..G5 -> verdict.json. ONLY a go=True installs.
#
# FAIL-CLOSED: requires APPROVED=1 DRY_RUN=0. Any failure restores kvg + ee69ebc2.
set -u
APPROVED=${APPROVED:-0}
DRY_RUN=${DRY_RUN:-1}
S=/home/albus/strata166
W=$S/tmp/w1044
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$S/data/strata-huihui-ud-iq4_xs.log
WANT_OLD=a85743d7f554159e8ac1e2d432d2e5ea
WANT_NEW=3b758f88ddad25cdad236be267810a9e
WANT_CFG=ee69ebc272ce41a116f50ecb3bf0edc2
WANT_NEWCFG=3dde88012592
PROG=$W/window.log

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

if [ "$APPROVED" != 1 ] || [ "$DRY_RUN" != 0 ]; then
  echo "DRY RUN (APPROVED=$APPROVED DRY_RUN=$DRY_RUN): no production change."
  echo "  expected downtime 20-30 min (EXTRAPOLATED, NOT measured); hard cap 45 min."
  exit 0
fi

mkdir -p "$W"; : > "$PROG"
log "=== W1044 install window START; APPROVED=1; spec LONGCTX_GATE.md (W1044 revision) ==="

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
  log "RESTORE start (rc=$rc)"
  for n in A B C D srv; do docker rm -f q44_$n >/dev/null 2>&1; done
  if [ -f "$W/cfg_w1044.bak" ]; then
    cp -f "$W/cfg_w1044.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_w1044.bak" "$CFG"
    log "config restored to $(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12)"
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  fi
  wait_health 420 || log "WARN: health did not return during restore"
  log "RESTORE DONE cfg=$(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
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
for f in qq_long.py set32k.ids.json cfgP_kvg.json cfgP_attn.json cfg_new.json \
         longctx_needle.py judge.py kl_extract.py timing.json; do
  [ -s "$W/$f" ] || fail "missing $W/$f"
done
md5sum "$W/cfg_new.json" | grep -q "$WANT_NEWCFG" || fail "cfg_new.json md5 mismatch"
grep -q "STRATA_GFX906_ATTN_DP4A" "$S/deploy/params/PARAM_REGISTER.tsv" \
  || fail "switch not ADOPTED in register (D5 would REFUSE)"
cp -f "$CFG" "$W/cfg_w1044.bak"
LOGLINES=$(wc -l < "$LOG")       # P493: never grep the whole append-only log
log "preconditions OK; LOGLINES=$LOGLINES; DOWNTIME STARTS NOW"
T0=$(date +%s)
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 2
[ "$(pgrep -c -x strata-host)" = 0 ] || fail "engine still alive"

# ------------------------------------------------------------------ G1/G2/G3
run_arm() {  # $1 tag  $2 cfg  $3 qq --env string (may be empty)  $4 outer docker -e (may be empty)
  local tag=$1 cfg=$2 qqenv=$3 outenv=$4
  log "=== logits arm $1 (cfg=$2 qqenv='${3:-}' outer='${4:-}') ==="
  local eargs=""; [ -n "$outenv" ] && eargs="-e $outenv"
  docker run --rm --name q44_$tag --device=/dev/kfd --device=/dev/dri $eargs \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 1800 python3 /w/qq_long.py prompt --config /w/$cfg \
              --out /w/L_$tag --ids /w/set32k.ids.json --gpu-experts ${qqenv}" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $tag rc=$rc files=$(ls -1 $W/L_$tag 2>/dev/null | wc -l)"
  if [ "$rc" != 0 ]; then tail -12 "$W/L_$tag/stderr.txt" 2>/dev/null | tee -a "$PROG"; fi
  return $rc
}
run_arm A cfgP_kvg.json  ""                                  ""            || fail "arm A failed"
run_arm B cfgP_attn.json ""                                  ""            || fail "arm B failed"
run_arm C cfgP_attn.json "--env STRATA_GFX906_ATTN_DP4A=1"   ""            || fail "arm C failed"
run_arm D cfgP_kvg.json  ""                                  "QQ_KV=fp16"  || fail "arm D failed"

log "=== G1/G2/G3: extract KL + build floor ==="
docker run --rm -v "$W":/w "$IMG" bash -lc "python3 /w/kl_extract.py \
  /w/L_A /w/L_B /w/L_C /w/L_D --out /w/kl.json --floor /w/floor.txt" \
  >> "$PROG" 2>&1 || fail "kl_extract failed"
grep -E "^[0-9A-Za-z]+ n=|^FLOOR=" "$PROG" | tail -6
FLOOR=$(cat "$W/floor.txt")
log "FLOOR=$FLOOR  kl.json=$(wc -c < $W/kl.json) bytes"
[ "$FLOOR" = 1 ] || log "WARN: G1 floor broken -> judge will say NO-GO"

# ------------------------------------------------------------------ G4 task grid
srv_up() {  # $1 outer env (may be empty)
  docker rm -f q44_srv >/dev/null 2>&1
  local eargs=""; [ -n "${1:-}" ] && eargs="-e $1"
  docker run -d --name q44_srv --network host --device=/dev/kfd --device=/dev/dri $eargs \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /w/cfgP_attn.json --port 8090" \
    >> "$PROG" 2>&1
  wait_health 480
}
srv_down() { docker rm -f q44_srv >/dev/null 2>&1; sleep 3; }
log "=== G4 needle grid: OFF (production-shaped kvg candidate, switch off) ==="
srv_up "" || fail "temp server (off) did not come up"
python3 "$W/longctx_needle.py" --label off --out "$W/grid_off.json" >> "$PROG" 2>&1 \
  || { tail -12 "$PROG"; fail "needle off failed"; }
srv_down
log "=== G4 needle grid: ON (ATTN_DP4A=1) ==="
srv_up "STRATA_GFX906_ATTN_DP4A=1" || fail "temp server (on) did not come up"
python3 "$W/longctx_needle.py" --label on --out "$W/grid_on.json" >> "$PROG" 2>&1 \
  || { tail -12 "$PROG"; fail "needle on failed"; }
srv_down
grep -E "^SUMMARY|^off |^on " "$PROG" | tail -22

# ------------------------------------------------------------------ verdict
log "=== judge G1..G5 (pre-registered, no editing criteria now) ==="
python3 "$W/judge.py" --grid-off "$W/grid_off.json" --grid-on "$W/grid_on.json" \
  --kl "$W/kl.json" --timing "$W/timing.json" --floor-ok "$FLOOR" \
  --out "$W/verdict.json" >> "$PROG" 2>&1
JRC=$?
tail -14 "$PROG"
[ "$JRC" = 0 ] || fail "VERDICT NO-GO (judge rc=$JRC) -> NOT installing, restoring production"
python3 - "$W/verdict.json" <<'PY' || fail "verdict.json is not go=True"
import json,sys
v=json.load(open(sys.argv[1]))
print("VERDICT", {k:v[k] for k in ("G1","G2","G3","G4","G5","go")})
raise SystemExit(0 if v.get("go") is True else 1)
PY

# ------------------------------------------------------------------ install
log "=== INSTALL attn (gate is go=True) ==="
cp -f "$W/cfg_new.json" "$CFG" || fail "cannot write config"
md5sum "$CFG" | grep -q "$WANT_NEWCFG" || fail "installed config md5 mismatch"
docker start $C >/dev/null || fail "docker start"
wait_health 420 || fail "health did not return after install"
NEW=$(pgrep -a -x strata-host | awk '{print $2}')
[ "$NEW" = "/data/bin/strata-0.1.57-attn" ] || fail "running engine is $NEW, not attn"
PID=$(pgrep -x strata-host | head -1)
tr '\0' '\n' < /proc/$PID/environ | grep -q '^STRATA_GFX906_ATTN_DP4A=1$' \
  || fail "switch env NOT present in the running process -> the port would be inert"
log "engine=$NEW  switch env verified in /proc/$PID/environ"
tail -n +$((LOGLINES+1)) "$LOG" > "$W/new_start.log"     # P493: slice only new lines
grep -q "expert cache 8301 slots" "$W/new_start.log" || log "WARN: no 8301-slot line in new slice"
if grep -q "kv-grow is off" "$W/new_start.log"; then fail "kv-grow is OFF in new slice"; fi
if grep -q "could not map" "$W/new_start.log"; then fail "could not map in new slice"; fi
log "=== smoke: one short chat ==="
curl -s -m 180 -H 'Content-Type: application/json' \
  -d '{"model":"x","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":8,"temperature":0}' \
  http://127.0.0.1:8090/v1/chat/completions > "$W/smoke.json" || fail "smoke request failed"
grep -q '"content"' "$W/smoke.json" || fail "smoke response has no content"
log "smoke ok: $(head -c 160 $W/smoke.json)"
T1=$(date +%s)
log "DONE installed exe=$NEW cfg=$(md5sum "$CFG" | cut -d' ' -f1) downtime=$((T1-T0))s"
trap - EXIT
