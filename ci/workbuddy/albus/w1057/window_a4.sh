#!/bin/bash
# W1057/R74 window: 4 arms through the production container, STRATA_DUMP_FIRST_LOGITS
# full-vocab first-window logits per request. Arms:
#   A1a / A1b : exe=hc4b  (cross-process noise floor, 2 processes)
#   A2        : exe=a4probe, no env  (patch-inert check: same numerics as hc4b)
#   B         : exe=a4probe, STRATA_A4_SIM=1  (int4 activation simulation)
# Identical deviation in ALL arms: --conversation-cache-mib 0 (kill cross-restart prompt
# reuse so every request re-runs the GEMMs; verified via usage.reused==0).
# trap restore = cp cfg back + cold restart (the W1051 lesson: restore = cp + restart).
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1057
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_a4.log
mkdir -p "$W" "$S/data/w1057"
: > "$LOG"
cp -f "$CFG" "$W/cfg_a4_pre.bak" || exit 1

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
restore() {
  cp -f "$W/cfg_a4_pre.bak" "$CFG" || true
  docker stop -t 25 "$C" >/dev/null 2>&1 || true
  sleep 2
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "RESTORE: health ok after ${i}s"; return 0; fi
    sleep 1
  done
  log "RESTORE FAIL"; return 1
}
trap restore EXIT INT TERM

arm() { # $1=tag $2=exe-file $3=a4sim 0/1
  local tag=$1 exe=$2 a4=$3
  log "=== arm $tag exe=$exe a4sim=$a4 ==="
  python3 - "$CFG" "$W/cfg_a4_pre.bak" "$exe" "$a4" "$tag" <<'PY'
import json, sys
live, orig, exe, a4, tag = sys.argv[1:6]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_DUMP_FIRST_LOGITS"] = "/data/w1057/fl_" + tag
# identical deviation in all arms (quant_quality skill 5): force GPU MMQ path so the
# CUDA activation quantizer actually runs; production runs CPU_SHARE=auto which can
# park small prefills on the host GEMM (W1057 run-1: all arms bit-identical there).
env["STRATA_PREFILL_CPU_SHARE"] = "0"
if a4 == "1":
    env["STRATA_A4_SIM"] = "1"
d["exe"] = "/data/bin/strata-0.1.57-" + exe
d["env"] = env
args = []
skip = False
for a in d.get("args", []):
    if skip:
        skip = False
        continue
    if a == "--conversation-cache-mib":
        args += [a, "0"]   # identical deviation in all arms
        skip = True
        continue
    args += [a]
d["args"] = args
json.dump(d, open(live, "w", encoding="utf-8"), indent=2)
print("cfg armed: exe=%s a4=%s dump=%s env_n=%d" % (d["exe"], a4, env["STRATA_DUMP_FIRST_LOGITS"], len(env)))
PY
  rm -f "$S/data/w1057/fl_${tag}".[0-9]*
  docker stop -t 25 "$C" >/dev/null 2>&1 || true
  sleep 2
  docker start "$C" >/dev/null 2>&1 || { log "arm $tag: docker start FAIL"; return 1; }
  local ok=0
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "arm $tag: health ok after ${i}s"; ok=1; break; fi
    sleep 1
  done
  [ "$ok" = 1 ] || { log "arm $tag: HEALTH FAIL"; return 1; }
  python3 - "$tag" <<'PY' | tee -a "$LOG"
import json, sys, urllib.request
tag = sys.argv[1]
filler = "The quick brown fox jumps over the lazy dog while the river flows quietly past the old mill. "
prompts = [
    "What is the capital of France? Answer in one sentence.",
    "Read this text and summarize in one sentence: " + filler * 8,
    "Read this text and summarize in one sentence: " + filler * 16,
    "Read this text and summarize in one sentence: " + filler * 24,
    "Read this text and summarize in one sentence: " + filler * 40,
    "Explain what a binary search tree is in two sentences.",
]
for i, txt in enumerate(prompts):
    body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": txt}],
                       "max_tokens": 24, "temperature": 0}).encode()
    req = urllib.request.Request("http://localhost:8090/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    u = d.get("usage", {})
    print("arm %s req %d usage %s" % (tag, i, json.dumps(u, sort_keys=True)))
PY
  ls -la "$S/data/w1057/" | grep "fl_${tag}" >>"$LOG" 2>&1
}

arm A1a hc4b 0
arm A1b hc4b 0
arm A2 a4probe 0
arm B a4probe 1
log "=== all arms done; restoring production ==="
