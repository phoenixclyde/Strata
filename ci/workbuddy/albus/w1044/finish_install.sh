#!/bin/bash
# W1044-B finish: repair the config/process mismatch left by the false-negative
# env check, then cold-restart to PROVE the installed config survives a restart.
# Any failure -> rollback to kvg + ee69ebc2 and start production.
set -u
APPROVED=${APPROVED:-0}
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1044
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$S/data/strata-huihui-ud-iq4_xs.log
WANT_NEWCFG=3dde88012592
WANT_OLDCFG=ee69ebc272ce41a116f50ecb3bf0edc2
PROG=$W/finish.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
if [ "$APPROVED" != 1 ]; then echo "DRY RUN (pass APPROVED=1)"; exit 0; fi

wait_health() {
  local t0=$1 t=$1
  while [ "$t" -gt 0 ]; do
    curl -s -m 5 localhost:8090/health 2>/dev/null | grep -qE '"status": *"ok"' \
      && { log "health ok after $((t0-t))s"; return 0; }
    sleep 3; t=$((t-3))
  done
  return 1
}
restore() {
  local rc=$?
  log "FINISH RESTORE (rc=$rc) -> kvg + ee69ebc2"
  cp -f "$W/cfg_w1044b.bak" "$CFG" 2>/dev/null || sudo -n cp -f "$W/cfg_w1044b.bak" "$CFG"
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
  else
    docker restart -t 30 $C >/dev/null 2>&1
  fi
  wait_health 420 || log "WARN health did not return"
  log "ROLLED BACK cfg=$(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12) exe=$(pgrep -a -x strata-host | awk '{print $2}')"
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = 1 ] || { log "FAIL: not exactly 1 engine"; exit 1; }
docker inspect -f '{{.State.Running}}' $C | grep -q true || { log "FAIL: container not running"; exit 1; }
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-attn" ] \
  || { log "FAIL: running engine is not attn"; exit 1; }
md5sum "$W/cfg_new.json" | grep -q "$WANT_NEWCFG" || { log "FAIL: cfg_new md5"; exit 1; }
[ -f "$W/cfg_w1044b.bak" ] || { log "FAIL: rollback backup missing"; exit 1; }

# --- verify the switch from INSIDE the container as root (host user cannot read /proc/PID/environ)
CPID=$(docker exec $C pgrep -x strata-host | head -1 | tr -d '\r')
log "container engine pid=$CPID"
docker exec $C cat /proc/$CPID/environ | tr '\0' '\n' | grep -q '^STRATA_GFX906_ATTN_DP4A=1$' \
  || { log "FAIL: switch env absent inside container"; exit 1; }
log "switch env VERIFIED inside container (correct sampling surface)"

# --- repair disk/running mismatch
cp -f "$W/cfg_new.json" "$CFG" || { log "FAIL: cannot write config"; exit 1; }
md5sum "$CFG" | grep -q "$WANT_NEWCFG" || { log "FAIL: installed cfg md5"; exit 1; }
log "config now $(md5sum "$CFG" | cut -d' ' -f1) (exe=attn, env=10)"

# --- cold restart to prove persistence
LOGLINES=$(wc -l < "$LOG")
log "COLD RESTART starts now (LOGLINES=$LOGLINES)"
T0=$(date +%s)
docker restart -t 30 $C >/dev/null || { log "FAIL: docker restart"; exit 1; }
wait_health 420 || { log "FAIL: health after restart"; exit 1; }
NEW=$(pgrep -a -x strata-host | awk '{print $2}')
[ "$NEW" = "/data/bin/strata-0.1.57-attn" ] || { log "FAIL: engine after restart is $NEW"; exit 1; }
md5sum "$CFG" | grep -q "$WANT_NEWCFG" || { log "FAIL: cfg changed across restart"; exit 1; }
CPID2=$(docker exec $C pgrep -x strata-host | head -1 | tr -d '\r')
docker exec $C cat /proc/$CPID2/environ | tr '\0' '\n' | grep -q '^STRATA_GFX906_ATTN_DP4A=1$' \
  || { log "FAIL: switch env lost across restart"; exit 1; }
log "post-restart: exe=$NEW cfg=$(md5sum "$CFG" | cut -d' ' -f1 | cut -c1-12) switch=ON (pid=$CPID2)"
tail -n +$((LOGLINES+1)) "$LOG" > "$W/new_start_b.log"     # P493: new slice only
grep -q "expert cache 8301 slots" "$W/new_start_b.log" || log "WARN: no 8301-slot line"
if grep -q "kv-grow is off" "$W/new_start_b.log"; then log "FAIL: kv-grow OFF"; exit 1; fi
if grep -q "could not map" "$W/new_start_b.log"; then log "FAIL: could not map"; exit 1; fi
log "=== smoke ==="
curl -s -m 180 -H 'Content-Type: application/json' \
  -d '{"model":"x","messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":8,"temperature":0}' \
  http://127.0.0.1:8090/v1/chat/completions > "$W/smoke_b.json" || { log "FAIL: smoke request"; exit 1; }
grep -q '"content"' "$W/smoke_b.json" || { log "FAIL: smoke response"; exit 1; }
log "smoke ok: $(head -c 150 $W/smoke_b.json)"
T1=$(date +%s)
log "DONE FINISH downtime=$((T1-T0))s  exe=$NEW cfg=$(md5sum "$CFG" | cut -d' ' -f1)"
trap - EXIT
