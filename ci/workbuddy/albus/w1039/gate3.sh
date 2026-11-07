#!/bin/bash
# W1039/P457 phase 1: is the packed 12-in-16 reduction (REDUCE12) the thing that moved the numbers?
#
# The confound, read off the source after the fp16 gate came back at 0.038 KL:
#   control  runs attn_chunk_kernel<M,false,true>      (production env has no ATTN_REDUCE12)
#   OPT arms run attn_chunk_kernel<M,false,true,true,O> (STRATA_ATTN_OPT_SWZ hard-codes REDUCE12=true)
# so every "dot instruction vs baseline" number so far also changed the reduction.  This window changes
# ONLY the reduction, on the production binary: no rebuild, one env key.
#
#   arm A2  b12180, no extra env            -> cross-binary/cross-session floor against g2_A.tsv
#   arm R12 b12180, ATTN_REDUCE12=1         -> the reduction alone
#
# One stop, one start; arms run in throwaway containers while production is down.
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
PROG=$W/gate3.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  local rc=$?
  docker rm -f qq3_A2 qq3_R12 >/dev/null 2>&1
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
[ -f "$W/g2_A.tsv" ] || fail "reference g2_A.tsv missing"
[ -f "$W/qq_k8v4.py" ] || fail "qq_k8v4.py missing"

log "=== config for b12180 ==="
python3 - "$CFG" "$W" <<'PY' | tee -a "$PROG"
import io, json, sys
cfg, w = sys.argv[1], sys.argv[2]
d = json.load(io.open(cfg, encoding="utf-8-sig"))
d["exe"] = "/data/bin/strata-0.1.57-b12180"
a = d["args"]
for i, x in enumerate(a):
    if x == "--expert-profile-save" and i + 1 < len(a):
        a[i + 1] = w + "/qq-profile7.bin"
d["args"] = a
json.dump(d, io.open(w + "/qq_cfg7.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
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
  docker run --rm --name qq3_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 260 python3 /w/qq_k8v4.py run --config /w/qq_cfg7.json --out /w/g3_$1.tsv --ids /src/data/quant_quality/v1/set.ids.json --gpu-experts $extra" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc  $( [ -f "$W/g3_$1.tsv" ] && wc -l < "$W/g3_$1.tsv" || echo 'no tsv')"
  docker rm -f qq3_$1 >/dev/null 2>&1
  return $rc
}

run_arm A2 "" || { log "FAIL arm A2 - abort"; docker start $C >/dev/null; sleep 15; exit 1; }
run_arm R12 "STRATA_GFX906_ATTN_REDUCE12=1" || log "WARN arm R12 failed"

log "=== compare ==="
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && echo '---- A2 vs g2_A  (cross-binary / cross-session floor) ----'; \
   python3 /w/qq_k8v4.py compare /w/g3_A2.tsv /w/g2_A.tsv 2>&1 | tail -10; \
   echo '---- A2 vs R12 (the reduction alone) ----'; \
   python3 /w/qq_k8v4.py compare /w/g3_A2.tsv /w/g3_R12.tsv 2>&1 | tail -12" 2>&1 | tee -a "$PROG"

log "=== restore ==="
docker start $C >/dev/null || fail "docker start"
for i in $(seq 1 140); do
  curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
  sleep 3
done
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "restored exe wrong"
log "DONE"
trap - EXIT
