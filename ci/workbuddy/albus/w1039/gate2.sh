#!/bin/bash
# W1039 numeric gate #2: fp16 query + v_dot2_f32_f16 (pa6, ATTN_F16D=1) against the same binary with it off.
# Same three arms and the same yardstick deviation as gate.sh (--kv k8v4, else kv_mode 0 and the path is inert).
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
PROG=$W/gate2.log
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  local rc=$?
  docker rm -f qq2_A qq2_Ab qq2_B >/dev/null 2>&1
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

log "=== config for pa6 ==="
python3 - "$CFG" "$W" <<'PY' | tee -a "$PROG"
import io, json, sys
cfg, w = sys.argv[1], sys.argv[2]
d = json.load(io.open(cfg, encoding="utf-8-sig"))
d["exe"] = "/data/bin/strata-0.1.57-pa6"
a = d["args"]
for i, x in enumerate(a):
    if x == "--expert-profile-save" and i + 1 < len(a):
        a[i + 1] = w + "/qq-profile6.bin"
d["args"] = a
json.dump(d, io.open(w + "/qq_cfg6.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("cfg exe=", d["exe"], "args=", len(a))
PY

log "=== stop production ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 3
[ "$(pgrep -c -x strata-host)" = "0" ] || fail "engine still alive"
USED=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -1 | grep -o '[0-9]\{6,\}' | head -1)
log "VRAM used after stop: ${USED:-unknown}"

run_arm() {   # $1 tag  $2 var=value (may be empty)
  log "=== arm $1 ($2) ==="
  local extra=""
  [ -n "$2" ] && extra="--env $2"
  docker run --rm --name qq2_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 240 python3 /w/qq_k8v4.py run --config /w/qq_cfg6.json --out /w/g2_$1.tsv --ids /src/data/quant_quality/v1/set.ids.json --gpu-experts $extra" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc  $( [ -f "$W/g2_$1.tsv" ] && wc -l < "$W/g2_$1.tsv" || echo 'no tsv')"
  docker rm -f qq2_$1 >/dev/null 2>&1
  return $rc
}

run_arm A  "" || { log "FAIL arm A - abort"; docker start $C >/dev/null; sleep 15; exit 1; }
run_arm Ab "" || log "WARN arm Ab failed"
run_arm B  "STRATA_GFX906_ATTN_F16D=1" || log "WARN arm B failed"

log "=== compare ==="
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && python3 /w/qq_k8v4.py compare /w/g2_A.tsv /w/g2_Ab.tsv 2>&1 | tail -12; \
   echo '---- A vs B (fp16 dot2) ----'; \
   python3 /w/qq_k8v4.py compare /w/g2_A.tsv /w/g2_B.tsv 2>&1 | tail -12" 2>&1 | tee -a "$PROG"

log "=== restore ==="
docker start $C >/dev/null || fail "docker start"
for i in $(seq 1 140); do
  curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
  sleep 3
done
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "restored exe wrong"
log "DONE"
trap - EXIT
