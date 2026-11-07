#!/bin/bash
# W1049c: A2 addendum -- G1 for LDS_PAD alone + the production combo arm (DP4A+PAD).
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1049
IMG=strata-gfx906:0.2.11-101
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_r103c.log
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
  log "RESTORE FAIL"; return 1
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
  docker stop -t 25 "$C" >/dev/null 2>&1 || true; sleep 2
  docker start "$C" >/dev/null 2>&1 || fail "docker start"
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "health ok ${i}s"; return 0; fi
    sleep 1
  done
  fail "health timeout"
}
chat_uniq() {
  python3 - "$W/$1" "$2" "$3" <<'PY'
import json, sys, urllib.request
txt = open(sys.argv[1], encoding="utf-8").read() + " Unique run marker %s end." % sys.argv[3]
body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": int(sys.argv[2]), "temperature": 0}).encode()
req = urllib.request.Request("http://localhost:8090/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=1800) as r:
    print("usage", json.loads(r.read()).get("usage"))
PY
}
perf_combo() {
  log "=== PERF combo DP4A+LDS_PAD ==="
  set_cfg /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_DP4A=1 STRATA_GFX906_ATTN_LDS_PAD=1
  restart
  chat_uniq p2500.txt 8 "warm-combo" >/dev/null 2>&1 || true
  local off n
  for n in 1 2 3; do
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p2500.txt 16 "combo-2k5-$n" >>"$LOG" 2>&1 || fail "2k5"
    tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'prefill timing:' | head -1 | sed "s/^/P2K5 combo r$n /" >>"$W/phase_b.txt"
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p8000.txt 16 "combo-8k-$n" >>"$LOG" 2>&1 || fail "8k"
    tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'prefill timing:' | head -1 | sed "s/^/P8K combo r$n /" >>"$W/phase_b.txt"
  done
  off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
  chat_uniq p2500.txt 400 "combo-dec" >>"$LOG" 2>&1 || fail "decode"
  tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'strata serve: prompt' | tail -1 | sed "s/^/DEC combo /" >>"$W/phase_b.txt"
}
dump_arm() {
  local tag=$1; shift
  log "=== DUMP $tag env=$* ==="
  python3 - "$W/cfg_dump_$tag.json" "$W/cfg_original.json" "$@" <<'PY'
import json, sys
dst, orig = sys.argv[1], sys.argv[2]
pairs = [a.split("=", 1) for a in sys.argv[3:]]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
for k in list(env):
    if k.startswith("STRATA_GFX906_ATTN_") or k in ("STRATA_GFX906_ATTN_REDUCE12", "STRATA_GFX906_ROUTE_DPP", "STRATA_GFX906_Q8_GATHER8"):
        env.pop(k, None)
for k, v in pairs:
    env[k] = v
d["exe"] = "/data/bin/strata-0.1.57-hc4b"; d["env"] = env
json.dump(d, open(dst, "w", encoding="utf-8"), indent=2)
PY
  local envs=""
  for kv in "$@"; do envs="$envs --env $kv"; done
  docker run --rm --name q49_$tag --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v /home/albus/strata166/pr/k10:/src -v "$W":/w "$IMG" \
    bash -lc "timeout 1800 python3 /w/qq_long.py prompt --config /w/cfg_dump_$tag.json \
      --out /w/L_$tag --ids /w/set32k_v2.ids.json --gpu-experts $envs" >>"$LOG" 2>&1 || fail "dump $tag"
  log "dump $tag ok"
}
pcompare() {
  log "=== pcompare $1 vs $2 ==="
  docker run --rm -v "$W":/w "$IMG" bash -lc "python3 /w/qq_long.py pcompare /w/L_$1 /w/L_$2" \
    | tee -a "$LOG" | sed "s/^/CMP $1 vs $2 /" >>"$W/pcompare_summary.txt"
}

log "WINDOW R103C STARTS"
perf_combo
log "DOWNTIME numeric starts"
docker stop -t 25 "$C" >/dev/null || fail "stop"
sleep 2
dump_arm c STRATA_GFX906_ATTN_LDS_PAD=1
dump_arm m STRATA_GFX906_ATTN_DP4A=1 STRATA_GFX906_ATTN_LDS_PAD=1
pcompare f c
pcompare f m
log "WINDOW R103C DONE"
exit 0
