#!/bin/bash
# W1039/P457 phase 3: is the bit-16 arm deterministic, and does the manual read match load8?
#   arm E8    pa8, no switch      -> pa8-vs-pa7 build floor
#   arm C16a  pa8 + CTLREAD=1     -> carries the DBG16 device print (manual codes vs load8 values)
#   arm C16b  pa8 + CTLREAD=1     -> SAME as C16a, second container: the determinism control
# The four switch arms measured so far are the same size but only 0.50-0.65 correlated, which one wrong
# index cannot produce.  Either the arm is not reproducible, or the print says exactly what differs.
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
PROG=$W/gate6.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  local rc=$?
  docker rm -f qq6_E8 qq6_C16a qq6_C16b >/dev/null 2>&1
  if [ "$(docker inspect -f '{{.State.Running}}' $C 2>/dev/null)" != "true" ]; then
    docker start $C >/dev/null 2>&1
    log "RESTORE: container started (rc=$rc)"
  fi
  for i in $(seq 1 40); do
    curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
    sleep 3
  done
}
trap restore EXIT
trap 'log signal; restore; exit 130' INT TERM

log "=== preconditions ==="
[ "$(pgrep -c -x strata-host)" = "1" ] || fail "expected 1 engine"
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "production is not b12180"
md5sum "$S/data/bin/strata-0.1.57-pa8" | tee -a "$PROG"

log "=== config for pa8 ==="
python3 - "$CFG" "$W" <<'PY' | tee -a "$PROG"
import io, json, sys
cfg, w = sys.argv[1], sys.argv[2]
d = json.load(io.open(cfg, encoding="utf-8-sig"))
d["exe"] = "/data/bin/strata-0.1.57-pa8"
a = d["args"]
for i, x in enumerate(a):
    if x == "--expert-profile-save" and i + 1 < len(a):
        a[i + 1] = w + "/qq-profile8.bin"
d["args"] = a
json.dump(d, io.open(w + "/qq_cfg8.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("cfg exe=", d["exe"], "args=", len(a), "env=", len(d.get("env", {})))
PY

log "=== stop production ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 3
[ "$(pgrep -c -x strata-host)" = "0" ] || fail "engine still alive"

run_arm() {   # $1 tag  $2 var=value (may be empty)
  log "=== arm $1 ($2) ==="
  local extra=""
  [ -n "$2" ] && extra="--env $2"
  docker run --rm --name qq6_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 260 python3 /w/qq_k8v4.py run --config /w/qq_cfg8.json --out /w/g6_$1.tsv --ids /src/data/quant_quality/v1/set.ids.json --gpu-experts $extra" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc  $( [ -f "$W/g6_$1.tsv" ] && wc -l < "$W/g6_$1.tsv" || echo 'no tsv')"
  docker rm -f qq6_$1 >/dev/null 2>&1
  return $rc
}

run_arm E8   ""                            || { log "FAIL arm E8 - abort"; docker start $C >/dev/null; sleep 15; exit 1; }
run_arm C16a "STRATA_GFX906_ATTN_CTLREAD=1" || log "WARN arm C16a failed"
run_arm C16b "STRATA_GFX906_ATTN_CTLREAD=1" || log "WARN arm C16b failed"

log "=== device print (manual read vs load8) ==="
grep -m6 "DBG16" "$PROG" | tee -a "$PROG" || log "no DBG16 line"

log "=== compare ==="
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && echo '---- E8 vs g5_E (pa8 vs pa7, no switch: build floor) ----'; \
   python3 /w/qq_k8v4.py compare /w/g6_E8.tsv /w/g5_E.tsv 2>&1 | tail -8; \
   echo '---- E8 vs C16a (manual read + late scale) ----'; \
   python3 /w/qq_k8v4.py compare /w/g6_E8.tsv /w/g6_C16a.tsv 2>&1 | tail -8; \
   echo '---- C16a vs C16b (SAME env, two containers: determinism) ----'; \
   python3 /w/qq_k8v4.py compare /w/g6_C16a.tsv /w/g6_C16b.tsv 2>&1 | tail -8" 2>&1 | tee -a "$PROG"

log "=== restore ==="
docker start $C >/dev/null || fail "docker start"
for i in $(seq 1 140); do
  curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
  sleep 3
done
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "restored exe wrong"
log "DONE"
trap - EXIT
