#!/bin/bash
# W1039/P457 phase 2 (R12 came back bit-identical, so the reduction is innocent):
#   arm E    pa7, no switch              -> pa7-vs-b12180 floor (is the new build behaviour-neutral?)
#   arm C16  pa7 + ATTN_CTLREAD=1        -> baseline arithmetic through the OPT path's manual K read
#                                           and the 64-group scale applied once per lane.  KL==0 => read innocent.
#   arm D32  pa7 + ATTN_F16Q=1           -> query rounded to fp16 and back, then the same fp32 fma.
# Control = arm E (same binary as C16/D32); g3_A2 (b12180) cross-checks the floor.
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
PROG=$W/gate5.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  local rc=$?
  docker rm -f qq5_E qq5_C16 qq5_D32 >/dev/null 2>&1
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
[ -f "$W/g3_A2.tsv" ] || fail "g3_A2.tsv missing"
md5sum "$S/data/bin/strata-0.1.57-pa7" | tee -a "$PROG"

log "=== config for pa7 ==="
python3 - "$CFG" "$W" <<'PY' | tee -a "$PROG"
import io, json, sys
cfg, w = sys.argv[1], sys.argv[2]
d = json.load(io.open(cfg, encoding="utf-8-sig"))
d["exe"] = "/data/bin/strata-0.1.57-pa7"
a = d["args"]
for i, x in enumerate(a):
    if x == "--expert-profile-save" and i + 1 < len(a):
        a[i + 1] = w + "/qq-profile7.bin"
d["args"] = a
json.dump(d, io.open(w + "/qq_cfg7p.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
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
  docker run --rm --name qq5_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 260 python3 /w/qq_k8v4.py run --config /w/qq_cfg7p.json --out /w/g5_$1.tsv --ids /src/data/quant_quality/v1/set.ids.json --gpu-experts $extra" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc  $( [ -f "$W/g5_$1.tsv" ] && wc -l < "$W/g5_$1.tsv" || echo 'no tsv')"
  docker rm -f qq5_$1 >/dev/null 2>&1
  return $rc
}

run_arm E   ""                                 || { log "FAIL arm E - abort"; docker start $C >/dev/null; sleep 15; exit 1; }
run_arm C16 "STRATA_GFX906_ATTN_CTLREAD=1"     || log "WARN arm C16 failed"
run_arm D32 "STRATA_GFX906_ATTN_F16Q=1"        || log "WARN arm D32 failed"

log "=== compare ==="
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && echo '---- E vs g3_A2 (pa7 vs b12180, no switch: build floor) ----'; \
   python3 /w/qq_k8v4.py compare /w/g5_E.tsv /w/g3_A2.tsv 2>&1 | tail -10; \
   echo '---- E vs C16 (manual K read + late scale, fp32 fma) ----'; \
   python3 /w/qq_k8v4.py compare /w/g5_E.tsv /w/g5_C16.tsv 2>&1 | tail -12; \
   echo '---- E vs D32 (fp16 query round-trip, fp32 fma) ----'; \
   python3 /w/qq_k8v4.py compare /w/g5_E.tsv /w/g5_D32.tsv 2>&1 | tail -12" 2>&1 | tee -a "$PROG"

log "=== restore ==="
docker start $C >/dev/null || fail "docker start"
for i in $(seq 1 140); do
  curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
  sleep 3
done
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "restored exe wrong"
log "DONE"
trap - EXIT
