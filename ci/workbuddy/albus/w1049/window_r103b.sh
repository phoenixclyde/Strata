#!/bin/bash
# W1049b: cache-busted perf re-run for the R103 arms. Each measured request appends a
# unique suffix so the prompt cache cannot absorb it. No numeric, no install.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1049
IMG=strata-gfx906:0.2.11-101
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_r103b.log
mkdir -p "$W"
: > "$LOG"
cp -f "$CFG" "$W/cfg_original.json" || exit 1

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  cp -f "$W/cfg_original.json" "$CFG" || true
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "RESTORE: health ok after ${i}s"; return 0; fi
    sleep 1
  done
  log "RESTORE FAIL"
  return 1
}
trap restore EXIT INT TERM

set_cfg() {
  local exe=$1; shift
  python3 - "$CFG" "$W/cfg_original.json" "$exe" "$@" <<'PY'
import json, sys
live, orig, exe = sys.argv[1], sys.argv[2], sys.argv[3]
pairs = [a.split("=", 1) for a in sys.argv[4:]]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
for k in list(env):
    if k.startswith("STRATA_GFX906_ATTN_") or k in ("STRATA_GFX906_ATTN_REDUCE12", "STRATA_GFX906_ROUTE_DPP", "STRATA_GFX906_Q8_GATHER8"):
        env.pop(k, None)
for k, v in pairs:
    env[k] = v
d["exe"] = exe; d["env"] = env
json.dump(d, open(live, "w", encoding="utf-8"), indent=2)
print("cfg exe=%s switches=%s" % (exe, pairs))
PY
}

restart() {
  docker stop -t 25 "$C" >/dev/null 2>&1 || true
  sleep 2
  docker start "$C" >/dev/null 2>&1 || fail "docker start"
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "health ok after ${i}s"; return 0; fi
    sleep 1
  done
  fail "health timeout"
}

chat_uniq() { # $1 base prompt file, $2 max_tokens, $3 nonce
  python3 - "$W/$1" "$2" "$3" <<'PY'
import json, sys, urllib.request
txt = open(sys.argv[1], encoding="utf-8").read() + " Unique run marker %s end." % sys.argv[3]
body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": int(sys.argv[2]), "temperature": 0}).encode()
req = urllib.request.Request("http://localhost:8090/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=1800) as r:
    d = json.loads(r.read())
u = d.get("usage") or {}
print("usage", u)
PY
}

perf_arm() {
  local label=$1 exe=$2; shift 2
  log "=== PERF2 ARM $label exe=$exe env=$* ==="
  set_cfg "$exe" "$@" || fail "set_cfg"
  restart
  chat_uniq p2500.txt 8 "warm-$label-0" >/dev/null 2>&1 || true
  local off n
  for n in 1 2 3; do
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p2500.txt 16 "$label-2k5-$n" >>"$LOG" 2>&1 || fail "2k5 $n"
    tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'prefill timing:' | head -1 \
      | sed "s/^/P2K5 $label r$n /" >>"$W/phase_b.txt"
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p8000.txt 16 "$label-8k-$n" >>"$LOG" 2>&1 || fail "8k $n"
    tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'prefill timing:' | head -1 \
      | sed "s/^/P8K $label r$n /" >>"$W/phase_b.txt"
  done
  off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
  chat_uniq p2500.txt 400 "$label-dec" >>"$LOG" 2>&1 || fail "decode"
  tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'strata serve: prompt' | tail -1 \
    | sed "s/^/DEC $label /" >>"$W/phase_b.txt"
  log "PERF2 ARM $label done"
}

log "WINDOW R103B STARTS"
perf_arm a_floor   /data/bin/strata-0.1.57-hc4b
perf_arm b_dpp     /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_DPP=1
perf_arm c_ldspad  /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_LDS_PAD=1
perf_arm d_red12   /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_REDUCE12=1
perf_arm e_dp4a    /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_DP4A=1
perf_arm f_r103x   /data/bin/strata-0.1.57-r103x
perf_arm g_route   /data/bin/strata-0.1.57-r103x STRATA_GFX906_ROUTE_DPP=1
perf_arm h_gather  /data/bin/strata-0.1.57-r103x STRATA_GFX906_Q8_GATHER8=1
perf_arm k_ilp     /data/bin/strata-0.1.57-r103ilp
log "WINDOW R103B DONE"
exit 0
