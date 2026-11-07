#!/bin/bash
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1047
CFG=$S/data/strata-huihui-ud-iq4_xs.json
NEWCFG=$W/cfg_new.json
BAK=$W/cfg_preinstall_w1047.bak
LOG=$W/install_hc4b.log
EXE=$S/data/bin/strata-0.1.57-hc4b
WANT_EXE_MD5=0533074826258d5f96c4b65bc0ad33df
mkdir -p "$W"; : > "$LOG"
log(){ echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail(){ log "FAIL: $*"; exit 1; }

rollback(){
  log "ROLLBACK: restoring config and restarting container"
  cp -f "$BAK" "$CFG.new" && mv -f "$CFG.new" "$CFG" || true
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    curl -s -m 3 localhost:8090/health 2>/dev/null | grep -q ok && { log "ROLLBACK health ok ${i}s"; return 0; }
    sleep 1
  done
  log "ROLLBACK health FAILED"
  return 1
}
trap rollback ERR INT TERM

[ -f "$NEWCFG" ] || fail "missing cfg_new"
[ -f "$EXE" ] || fail "missing candidate"
md5sum "$EXE" | grep -q "$WANT_EXE_MD5" || fail "candidate md5 mismatch"
cp -f "$CFG" "$BAK" || fail "backup config"
WANT_CFG=$(md5sum "$NEWCFG" | cut -d' ' -f1)
log "backup=$BAK want_cfg=$WANT_CFG"

log "INSTALL: stop container"
docker stop -t 25 "$C" >/dev/null || fail "docker stop"
sleep 2
cp -f "$NEWCFG" "$CFG.new" && mv -f "$CFG.new" "$CFG" || fail "install config"
log "INSTALL: config written $(md5sum "$CFG" | cut -d' ' -f1)"
docker start "$C" >/dev/null || fail "docker start"

ok=0
for i in $(seq 1 120); do
  r=$(curl -s -m 3 localhost:8090/health 2>/dev/null || true)
  if echo "$r" | grep -q ok; then ok=1; log "health ok after ${i}s"; break; fi
  sleep 1
done
[ "$ok" = 1 ] || fail "health timeout"

md5sum "$CFG" | grep -q "$WANT_CFG" || fail "config md5 mismatch after start"
docker exec "$C" md5sum /data/bin/strata-0.1.57-hc4b | grep -q "$WANT_EXE_MD5" || fail "disk engine md5 mismatch"
P=$(docker exec "$C" pgrep -x strata-host | head -1 | tr -d '\r')
[ -n "$P" ] || fail "engine process missing"
docker exec "$C" sh -lc "tr '\\0' '\\n' < /proc/$P/environ | grep -E 'STRATA_HC_DOWN_DP4A|STRATA_HC_DOWN_DP4A_MAX_T'" | tee -a "$LOG"
docker exec "$C" sh -lc "tr '\\0' '\\n' < /proc/$P/environ | grep -q 'STRATA_HC_DOWN_DP4A=1'" || fail "DP4A env missing"
docker exec "$C" sh -lc "tr '\\0' '\\n' < /proc/$P/environ | grep -q 'STRATA_HC_DOWN_DP4A_MAX_T=6'" || fail "MAX_T env missing"
log "running=$(docker inspect -f '{{.State.Status}}|{{.RestartCount}}' "$C")"
log "INSTALL DONE cfg=$WANT_CFG"
trap - ERR INT TERM
exit 0
