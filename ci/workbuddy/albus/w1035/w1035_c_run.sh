#!/bin/bash
# w1035_c_run.sh -- P392 option C: full-vocabulary prefill gate, REF vs RUN.
#
# Why this shape (and not `quant_quality run`):
#   `run` reads the text through the DECODE windows (--short-read).  That is the path on which
#   strata-0.1.57-010 spun at 64 W for 10 min (P392) and it is not the path #29953 touches.
#   `prompt` deletes --short-read, sets --prefill auto and dumps STRATA_DUMP_FIRST_LOGITS:
#   the batched PREFILL path's next-token logits, whole float32 vocabulary, 5 segments x
#   4 prefix lengths (256/512/768/1000) = 20 paired points.  `pcompare` then reports
#   top-1 and full-vocabulary KL(REF||RUN).
#
# Arms:  001   strata-0.1.57-001  (production, REF)
#        001b  strata-0.1.57-001  (same exe, fresh container -> the SELF-CONSISTENCY FLOOR)
#        010   strata-0.1.57-010  (K10: 0.9.0 tree + mmq head @4c1004c)
#
# Safety:  every arm runs inside its own throwaway container, so a hang is killed with
#          `docker rm -f`, not with a signal to a host process (P386: two engines on the card
#          once already cost a cold boot).  Per-arm `timeout`, wall-clock guard, trap restore.
#
#   bash w1035_c_run.sh --preflight     # read-only: checks only, never stops anything
#   bash w1035_c_run.sh --go            # the real run (production goes down)
set -uo pipefail

IMG=strata-gfx906:0.2.11-101
DATA=/home/albus/strata166/data
W=/home/albus/strata166/tmp/w1035
CFG=$DATA/strata-huihui-ud-iq4_xs.json
PROD=strata166-407
HEALTH=http://127.0.0.1:8090/health
ARM_TIMEOUT=270          # seconds per arm (4.5 min).  001 took 3.5 min for 5 DEOCDE segments;
                         # `prompt` is the batched path, so 20 short prompts must fit easily.
WALL_GUARD=720           # 12 min: past this, stop launching arms and restore
ARMS="001 001b 010"
T0=$(date +%s)

log() { printf '[%s +%3ds] %s\n' "$(date +%H:%M:%S)" "$(( $(date +%s) - T0 ))" "$*"; }

restore() {
  local rc=$?
  log "=== restore production container"
  docker start "$PROD" >/dev/null 2>&1
  for i in $(seq 1 40); do
    h=$(curl -s -m 4 $HEALTH || true)
    case "$h" in
      *'"ok"'*) log "production healthy after ~$(( i * 8 ))s"; break;;
    esac
    sleep 8
  done
  log "engine now: $(docker exec $PROD md5sum /data/bin/strata-0.1.57-001 2>/dev/null | cut -d' ' -f1)"
  exit $rc
}
trap restore EXIT INT TERM

# ---------------------------------------------------------------- preflight (read-only)
preflight() {
  local bad=0
  log "--- preflight (read-only, nothing is stopped)"
  docker image inspect "$IMG" >/dev/null 2>&1 && log "image OK  $IMG" || { log "MISSING image $IMG"; bad=1; }
  for b in strata-0.1.57-001 strata-0.1.57-010; do
    if [ -f "$DATA/bin/$b" ]; then log "bin  OK  $b  $(md5sum $DATA/bin/$b | cut -d' ' -f1)  $(stat -c%s $DATA/bin/$b) B"
    else log "MISSING bin $b"; bad=1; fi
  done
  [ -f "$CFG" ] && log "cfg  OK  $(md5sum $CFG | cut -d' ' -f1)" || { log "MISSING config"; bad=1; }
  if docker run --rm "$IMG" sh -lc 'test -f /src/data/quant_quality/v1/set.ids.json'; then
    log "ids  OK  /src/data/quant_quality/v1/set.ids.json"
  else
    log "MISSING set.ids.json"; bad=1
  fi
  docker run --rm "$IMG" sh -lc 'python3 -c "import numpy; print(\"numpy OK\", numpy.__version__)"' 2>&1 | tail -1
  log "prod $(docker inspect -f '{{.State.Status}} restarts={{.RestartCount}}' $PROD 2>/dev/null)"
  local n; n=$(docker ps --format '{{.Names}}' | grep -c '^qq' || true)
  log "stray qq_* containers: $n"
  mkdir -p "$W" && log "workdir $W"
  log "plan: arms [$ARMS]  per-arm timeout ${ARM_TIMEOUT}s  wall guard ${WALL_GUARD}s"
  log "expected downtime: stop 10s + 3 arms x ~150-180s + restore ~90s  =>  ~10-12 min (hard cap 17)"
  [ "$bad" = 0 ] && log "PREFLIGHT: PASS" || log "PREFLIGHT: FAIL"
  return $bad
}

# ---------------------------------------------------------------- configs
gen_configs() {
  python3 - "$CFG" "$W" <<'PY'
import json, sys, copy
src, w = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8-sig"))
for tag, exe in (("001", "strata-0.1.57-001"), ("001b", "strata-0.1.57-001"),
                 ("010", "strata-0.1.57-010")):
    e = copy.deepcopy(d)
    e["exe"] = "/data/bin/" + exe
    a = e.get("args", [])
    # never let the gate write a production profile: redirect the save path
    for i, x in enumerate(a):
        if x == "--expert-profile-save" and i + 1 < len(a):
            a[i + 1] = "/w1035/profile_%s.bin" % tag
    json.dump(e, open("%s/qq_%s.json" % (w, tag), "w"), indent=1)
    print("wrote %s/qq_%s.json  exe=%s  args=%d env=%d" % (w, tag, e["exe"], len(a), len(e.get("env", {}))))
PY
}

# ---------------------------------------------------------------- one arm
run_arm() {
  local tag=$1
  log "=== arm $tag  start"
  docker rm -f "qq_$tag" >/dev/null 2>&1 || true
  docker run --rm --name "qq_$tag" \
    --device=/dev/kfd --device=/dev/dri --ulimit memlock=-1:-1 --security-opt label=disable \
    -v /models:/models:ro -v "$DATA":/data -v "$W":/w1035 "$IMG" \
    bash -lc "set -o pipefail; timeout $ARM_TIMEOUT python3 /src/tools/quant_quality.py prompt \
      --config /w1035/qq_$tag.json --out /w1035/pq_$tag --gpu-experts 2>&1 | tail -12"
  local rc=$?
  log "=== arm $tag rc=$rc"
  docker rm -f "qq_$tag" >/dev/null 2>&1 || true
  if [ $rc -ne 0 ]; then
    log "!! arm $tag failed (rc=$rc); see $W/pq_$tag/stderr.txt"
  fi
  return $rc
}

# ---------------------------------------------------------------- main
MODE="${1:---preflight}"
if [ "$MODE" = "--preflight" ]; then preflight; trap - EXIT; exit $?; fi
if [ "$MODE" != "--go" ]; then echo "usage: $0 [--preflight|--go]"; trap - EXIT; exit 2; fi

preflight || { log "PREFLIGHT failed, not touching production"; trap - EXIT; exit 1; }

log "=== stop production"
docker stop -t 30 "$PROD" >/dev/null 2>&1
sleep 4
n=$(ps -eo args | grep -c '^/data/bin/strata-0\.1' || true)
used=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 'Used Memory (B)' | grep -o '[0-9]*$')
log "engines=$n vram_used=${used:-?}"
if [ "$n" != "0" ] || { [ -n "${used:-}" ] && [ "$used" -gt 2000000000 ]; }; then
  log "REFUSE: the GPU is still busy (P386). restoring."
  trap - EXIT; restore
fi

gen_configs || { log "config generation failed"; trap - EXIT; restore; }

for tag in $ARMS; do
  if [ $(( $(date +%s) - T0 )) -gt $WALL_GUARD ]; then log "wall guard hit, skipping $tag"; break; fi
  if ! run_arm "$tag"; then
    log "arm $tag failed -> aborting the remaining arms (a hang here is the answer, not a reason to keep burning the card)"
    break
  fi
done

log "=== compare (REF=pq_001, floor=pq_001b, gate=pq_010)"
docker run --rm -v "$W":/w1035 "$IMG" bash -lc "
python3 /src/tools/quant_quality.py pcompare /w1035/pq_001 /w1035/pq_001b /w1035/pq_010 2>&1 | tail -20" \
  | tee "$W/compare.txt"
log "=== done; restoring"
trap - EXIT
restore
