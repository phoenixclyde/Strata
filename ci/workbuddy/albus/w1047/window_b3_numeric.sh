#!/bin/bash
# W1047: B3 real-model numeric/task window. No install.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1047
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
LOG=$W/window_b3_numeric.log
CFG=$S/data/strata-huihui-ud-iq4_xs.json
mkdir -p "$W"
: > "$LOG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  log "RESTORE: starting production"
  docker rm -f q47_srv_off q47_srv_on q47_off q47_on >/dev/null 2>&1 || true
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 20 || true)
    if echo "$st" | grep -q ok; then log "RESTORE: health ok after ${i}s"; return 0; fi
    sleep 1
  done
  log "RESTORE FAIL"
  return 1
}
trap restore EXIT INT TERM

python3 - "$CFG" "$W/cfg_b3_off.json" "$W/cfg_b3_on.json" <<'PY'
import json,sys
src,dst0,dst1=sys.argv[1:]
d=json.load(open(src,encoding="utf-8-sig"))
d["exe"]="/data/bin/strata-0.1.57-hc4b"
for p in (dst0,dst1):
    json.dump(d,open(p,"w",encoding="utf-8"),indent=2)
print("cfg written",d["exe"],len(d["args"]),len(d["env"]))
PY

log "DOWNTIME STARTS NOW"
docker stop -t 25 "$C" >/dev/null || fail "docker stop"
sleep 2
[ "$(pgrep -c -x strata-host)" = 0 ] || fail "engine still alive"

run_logits() {
  local tag=$1 cfg=$2 val=$3
  log "=== logits arm $tag HC_DOWN_DP4A=$val ==="
  docker run --rm --name q47_$tag --device=/dev/kfd --device=/dev/dri \
    -e STRATA_HC_DOWN_DP4A=$val -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 1800 python3 /w/qq_long.py prompt --config /w/$cfg \
      --out /w/L3_$tag --ids /w/set32k_v2.ids.json --gpu-experts --env STRATA_HC_DOWN_DP4A=$val" \
    >> "$LOG" 2>&1
  local rc=$?
  log "arm $tag rc=$rc files=$(ls -1 $W/L3_$tag 2>/dev/null | wc -l)"
  [ "$rc" = 0 ] || { tail -12 "$W/L3_$tag/stderr.txt" 2>/dev/null | tee -a "$LOG"; return $rc; }
}

run_needle() {
  local tag=$1 cfg=$2 val=$3
  log "=== needle arm $tag HC_DOWN_DP4A=$val ==="
  docker rm -f q47_srv_$tag >/dev/null 2>&1 || true
  docker run -d --name q47_srv_$tag --device=/dev/kfd --device=/dev/dri \
    -p 8090:8090 -e STRATA_HC_DOWN_DP4A=$val -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /w/$cfg --port 8090" >/dev/null || return 1
  local ok=0
  for i in $(seq 1 90); do
    r=$(curl -s -m 3 localhost:8090/health 2>/dev/null || true)
    if echo "$r" | grep -q 'ok'; then ok=1; log "needle server ready ${i}s"; break; fi
    sleep 1
  done
  [ "$ok" = 1 ] || { docker logs --tail 20 q47_srv_$tag 2>&1 | tee -a "$LOG"; return 1; }
  python3 "$W/longctx_needle.py" --label "$tag" --out "$W/needle_$tag.json" \
    --lengths 16000,32000,64000 --depths 0,50,100 --timeout 900 >> "$LOG" 2>&1
  local rc=$?
  docker rm -f q47_srv_$tag >/dev/null 2>&1 || true
  return $rc
}

if [ "${SKIP_LOGITS:-0}" != 1 ]; then
  run_logits off cfg_b3_off.json 0 || fail "logits off"
  run_logits on  cfg_b3_on.json  1 || fail "logits on"
  log "=== pcompare off vs on ==="
  docker run --rm -v "$W":/w "$IMG" bash -lc "python3 /w/qq_long.py pcompare /w/L3_off /w/L3_on" | tee -a "$LOG" || fail "pcompare"
else
  log "SKIP_LOGITS=1; reusing completed L3_off/L3_on"
fi

run_needle off cfg_b3_off.json 0 || fail "needle off"
run_needle on  cfg_b3_on.json  1 || fail "needle on"
log "=== needle summaries ==="
grep 'SUMMARY label=' "$LOG" | tail -2
log "NUMERIC WINDOW DONE"
exit 0
