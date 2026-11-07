#!/bin/bash
# W1049: R103 completion window. Perf arms on the live container + numeric dumps with
# production stopped. No install. TRAP restores the original config and production.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1049
SRC=$S/pr/k10
IMG=strata-gfx906:0.2.11-101
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_r103.log
QL=/home/albus/strata166/tmp/w1047/qq_long.py
IDS=/home/albus/strata166/tmp/w1044/set32k_v2.ids.json
TOK=/home/albus/strata166/tmp/w1044/tokenizer.json
mkdir -p "$W"
: > "$LOG"
cp -f "$CFG" "$W/cfg_original.json" || exit 1
cp -f "$QL" "$W/qq_long.py" || exit 1
cp -f "$IDS" "$W/set32k_v2.ids.json" || exit 1

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  log "RESTORE: original config + production"
  cp -f "$W/cfg_original.json" "$CFG" || true
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "RESTORE: health ok after ${i}s"; return 0; fi
    sleep 1
  done
  log "RESTORE FAIL (production may be down)"
  return 1
}
trap restore EXIT INT TERM

# ---- prompt generation: deterministic text of roughly N tokens ----
python3 - "$W" <<'PY'
import sys
w = sys.argv[1]
base = "The quick brown fox jumps over the lazy dog near the river bank while the wind blows softly over the hills. "
for name, toks in (("p2500.txt", 2500), ("p8000.txt", 8000)):
    txt = (base * (toks // 10 + 2))[:toks * 4]
    open(w + "/" + name, "w", encoding="utf-8").write(txt)
print("prompts written")
PY

# ---- config writer: exe + full env set (switches explicit) ----
# usage: set_cfg <exe> <key=val ...>   (env starts from the original minus ATTN/REDUCE12/ROUTE/GATHER keys)
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
d["exe"] = exe
d["env"] = env
json.dump(d, open(live, "w", encoding="utf-8"), indent=2)
print("cfg exe=%s env_switches=%s" % (exe, pairs))
PY
}

restart() {
  docker stop -t 25 "$C" >/dev/null 2>&1 || true
  sleep 2
  docker start "$C" >/dev/null 2>&1 || fail "docker start"
  local ok=0
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then ok=1; log "health ok after ${i}s"; break; fi
    sleep 1
  done
  [ "$ok" = 1 ] || fail "health timeout"
}

chat() { # $1 prompt file, $2 max_tokens
  python3 - "$W/$1" "$2" <<'PY'
import json, sys, urllib.request
txt = open(sys.argv[1], encoding="utf-8").read()
body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": int(sys.argv[2]), "temperature": 0}).encode()
req = urllib.request.Request("http://localhost:8090/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=1800) as r:
    d = json.loads(r.read())
print("usage", d.get("usage"))
PY
}

# perf arm: $1 label, $2 exe, $3.. env pairs
perf_arm() {
  local label=$1 exe=$2; shift 2
  log "=== PERF ARM $label exe=$exe env=$* ==="
  set_cfg "$exe" "$@" || fail "set_cfg"
  restart
  chat p2500.txt 8 >/dev/null 2>&1 || true
  chat p2500.txt 8 >/dev/null 2>&1 || true
  local off=0
  off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
  chat p2500.txt 16 >>"$LOG" 2>&1 || fail "chat 2.5k"
  chat p2500.txt 16 >>"$LOG" 2>&1 || fail "chat 2.5k rep2"
  tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'prefill timing:' | tail -2 | tee -a "$LOG" | sed "s/^/PHASE2K5 $label /" >>"$W/phase_summary.txt"
  off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
  chat p8000.txt 16 >>"$LOG" 2>&1 || fail "chat 8k"
  chat p8000.txt 16 >>"$LOG" 2>&1 || fail "chat 8k rep2"
  tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'prefill timing:' | tail -2 | tee -a "$LOG" | sed "s/^/PHASE8K $label /" >>"$W/phase_summary.txt"
  off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
  chat p2500.txt 400 >>"$LOG" 2>&1 || fail "decode"
  tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'strata serve: prompt' | tail -1 | sed "s/^/DECODE $label /" >>"$W/phase_summary.txt"
  log "PERF ARM $label done"
}

# numeric dump: $1 tag, $2 exe, $3.. env pairs (production must be stopped)
dump_arm() {
  local tag=$1 exe=$2; shift 2
  log "=== DUMP ARM $tag exe=$exe env=$* ==="
  python3 - "$W/cfg_dump_$tag.json" "$W/cfg_original.json" "$exe" "$@" <<'PY'
import json, sys
dst, orig, exe = sys.argv[1], sys.argv[2], sys.argv[3]
pairs = [a.split("=", 1) for a in sys.argv[4:]]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
for k in list(env):
    if k.startswith("STRATA_GFX906_ATTN_") or k in ("STRATA_GFX906_ATTN_REDUCE12", "STRATA_GFX906_ROUTE_DPP", "STRATA_GFX906_Q8_GATHER8"):
        env.pop(k, None)
for k, v in pairs:
    env[k] = v
d["exe"] = exe; d["env"] = env
json.dump(d, open(dst, "w", encoding="utf-8"), indent=2)
PY
  local envs=""
  for kv in "$@"; do envs="$envs --env $kv"; done
  docker run --rm --name q49_$tag --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$SRC":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 1800 python3 /w/qq_long.py prompt --config /w/cfg_dump_$tag.json \
      --out /w/L_$tag --ids /w/set32k_v2.ids.json --gpu-experts $envs" >>"$LOG" 2>&1
  local rc=$?
  log "dump $tag rc=$rc files=$(ls -1 $W/L_$tag 2>/dev/null | wc -l)"
  [ "$rc" = 0 ] || { tail -8 "$W/L_$tag/stderr.txt" 2>/dev/null | tee -a "$LOG"; fail "dump $tag"; }
}

pcompare() {
  log "=== pcompare $1 vs $2 ==="
  docker run --rm -v "$W":/w "$IMG" bash -lc "python3 /w/qq_long.py pcompare /w/L_$1 /w/L_$2" \
    | tee -a "$LOG" | sed "s/^/CMP $1 vs $2 /" >>"$W/pcompare_summary.txt"
}

log "WINDOW R103 STARTS"
# ---------- phase 1: perf arms (production container) ----------
perf_arm a_floor   /data/bin/strata-0.1.57-hc4b
perf_arm b_dpp     /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_DPP=1
perf_arm c_ldspad  /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_LDS_PAD=1
perf_arm d_red12   /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_REDUCE12=1
perf_arm f_r103x   /data/bin/strata-0.1.57-r103x
perf_arm g_route   /data/bin/strata-0.1.57-r103x STRATA_GFX906_ROUTE_DPP=1
perf_arm h_gather  /data/bin/strata-0.1.57-r103x STRATA_GFX906_Q8_GATHER8=1
perf_arm k_ilp     /data/bin/strata-0.1.57-r103ilp

# ---------- phase 2: numeric dumps (production stopped) ----------
log "DOWNTIME (numeric phase) starts"
docker stop -t 25 "$C" >/dev/null || fail "docker stop"
sleep 2
dump_arm a /data/bin/strata-0.1.57-hc4b
dump_arm d /data/bin/strata-0.1.57-hc4b STRATA_GFX906_ATTN_REDUCE12=1
dump_arm f /data/bin/strata-0.1.57-r103x
dump_arm g /data/bin/strata-0.1.57-r103x STRATA_GFX906_ROUTE_DPP=1
dump_arm h /data/bin/strata-0.1.57-r103x STRATA_GFX906_Q8_GATHER8=1
dump_arm i /data/bin/strata-0.1.57-r103x STRATA_GFX906_ATTN_CTLREAD=1
dump_arm j /data/bin/strata-0.1.57-r103x STRATA_GFX906_ATTN_F16Q=1
dump_arm k /data/bin/strata-0.1.57-r103ilp

pcompare a f   # G1: r103x build floor must be bitwise
pcompare f g   # G1: A1 router DPP
pcompare f h   # G1: A5 gather8
pcompare a d   # P457: REDUCE12 probe
pcompare f i   # diag CTLREAD
pcompare f j   # diag F16Q
pcompare a k   # G2: A4 max-ilp

log "WINDOW R103 DONE"
exit 0
