#!/bin/bash
# W1041 numeric gate for the dp4a switch (skill: strata-quant-quality-gate), adapted:
#   * arms  A  = pa5, ATTN_DP4A off   (reference; the OPT=0 path is untouched by the patch)
#           Ab = pa5, ATTN_DP4A off   (self-consistency floor: a different container, same argv)
#           B  = pa5, ATTN_DP4A on    (the switch under test)
#   * DEVIATION: the yardstick forces `--kv fp16`, but kv_mode 0 means our dp4a dispatch
#     (`kv_mode == 3 || kv_mode == 1`, qsa_decode_attn.cu:1146) is never taken -> the gate would
#     measure nothing.  So a copy of the tool is used with FIXED `--kv k8v4` (production's format).
set -u
S=/home/albus/strata166
W=$S/tmp/w1041
SRC=$S/pr/port-all
IMG=strata-gfx906:0.2.11-101
C=strata166-407
CFG=$S/data/strata-huihui-ud-iq4_xs.json
PROG=$W/gate.log
mkdir -p "$W"
: > "$PROG"
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$PROG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  local rc=$?
  docker rm -f qq_A qq_Ab qq_B >/dev/null 2>&1
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
curl -s -m 10 localhost:8090/health | grep -q '"status": *"ok"' || fail "health"

log "=== tool copy with --kv k8v4 ==="
sed 's/"--kv", "fp16"/"--kv", "k8v4"/' "$SRC/tools/quant_quality.py" > "$W/qq_k8v4.py"
grep -n '"--kv", "k8v4"' "$W/qq_k8v4.py" | head -2 | tee -a "$PROG"
md5sum "$W/qq_k8v4.py" | tee -a "$PROG"

log "=== arm configs ==="
python3 - "$CFG" "$W" <<'PY' | tee -a "$PROG"
import io, json, sys
cfg, w = sys.argv[1], sys.argv[2]
d = json.load(io.open(cfg, encoding="utf-8-sig"))
d["exe"] = "/data/bin/strata-0.1.57-pa5"
a = d["args"]
# never write the production expert profile
for i, x in enumerate(a):
    if x == "--expert-profile-save" and i + 1 < len(a):
        a[i + 1] = w + "/qq-profile.bin"
d["args"] = a
json.dump(d, io.open(w + "/qq_cfg.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("cfg exe=", d["exe"], "args=", len(a))
PY

log "=== stop production ==="
docker stop -t 30 $C >/dev/null || fail "docker stop"
sleep 3
[ "$(pgrep -c -x strata-host)" = "0" ] || fail "engine still alive after stop"
USED=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -i used | head -1 | grep -o '[0-9]\{6,\}' | head -1)
log "VRAM used after stop: ${USED:-unknown}"
[ -n "${USED:-}" ] && [ "$USED" -gt 2000000000 ] && fail "VRAM still ${USED} B used, refusing to run"

run_arm() {   # $1 tag  $2 dp4a value
  log "=== arm $1 (DP4A=$2) ==="
  docker run --rm --name qq_$1 --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 240 python3 /w/qq_k8v4.py run --config /w/qq_cfg.json --out /w/run_$1.tsv --ids /src/data/quant_quality/v1/set.ids.json --gpu-experts --env STRATA_GFX906_ATTN_DP4A=$2" \
    >> "$PROG" 2>&1
  local rc=$?
  log "arm $1 rc=$rc  $( [ -f "$W/run_$1.tsv" ] && wc -l < "$W/run_$1.tsv" || echo 'no tsv')"
  docker rm -f qq_$1 >/dev/null 2>&1
  return $rc
}

run_arm A  0 || { log "FAIL arm A produced no data - not spending the other arms"; docker start $C >/dev/null; sleep 20; exit 1; }
run_arm Ab 0 || log "WARN arm Ab failed"
run_arm B  1 || log "WARN arm B failed"

log "=== compare ==="
docker run --rm -v "$SRC":/src -v "$W":/w "$IMG" bash -lc \
  "cd /src && python3 /w/qq_k8v4.py compare /w/run_A.tsv /w/run_Ab.tsv 2>&1 | tail -20; \
   echo '---- A vs B (the switch) ----'; \
   python3 /w/qq_k8v4.py compare /w/run_A.tsv /w/run_B.tsv 2>&1 | tail -20" 2>&1 | tee -a "$PROG"

log "=== restore ==="
docker start $C >/dev/null || fail "docker start"
for i in $(seq 1 140); do
  curl -s -m 5 localhost:8090/health 2>/dev/null | grep -q '"status": *"ok"' && { log "health ok after $((i*3))s"; break; }
  sleep 3
done
[ "$(pgrep -a -x strata-host | awk '{print $2}')" = "/data/bin/strata-0.1.57-b12180" ] || fail "restored exe wrong"
log "DONE"
trap - EXIT
