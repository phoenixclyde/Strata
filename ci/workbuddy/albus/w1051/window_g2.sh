#!/bin/bash
# W1051: R114 G2 window -- numeric gate (KL/top-1) + gdn phase A/B for
# STRATA_GFX906_GDN_DOT2 on candidate strata-0.1.57-r114.
# Single variable: production env kept verbatim; only GDN_DOT2 flips 0<->1.
# Service restarts and one stop window are counted in the log; trap restores cfg.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1051
IMG=strata-gfx906:0.2.11-101
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_g2.log
mkdir -p "$W"
: > "$LOG"
cp -f "$CFG" "$W/cfg_w1051_pre.bak" || exit 1
cp -f "$S/tmp/w1049/p2500.txt" "$S/tmp/w1049/p8000.txt" "$W/" || exit 1
cp -f "$S/tmp/w1044/qq_long.py" "$W/" || exit 1
cp -f "$S/tmp/w1049/set32k_v2.ids.json" "$W/" 2>/dev/null \
  || cp -f "$S/tmp/w1044/set32k_v2.ids.json" "$W/" || exit 1
echo "RESTARTS=0 STOPWINDOWS=0" > "$W/counter.txt"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

bump() { # $1 counter key
  python3 - "$W/counter.txt" "$1" <<'PY'
import io, sys
p, key = sys.argv[1], sys.argv[2]
d = dict(l.split("=", 1) for l in io.open(p).read().split() if "=" in l)
d[key] = str(int(d.get(key, "0")) + 1)
io.open(p, "w", newline="\n").write(" ".join("%s=%s" % (k, v) for k, v in d.items()))
print("counter", key, d[key])
PY
}

restore() {
  cp -f "$W/cfg_w1051_pre.bak" "$CFG" || true
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

mk_cfg() { # $1 out_path, $2 exe, $3 gdn_dot2 value
  python3 - "$1" "$W/cfg_w1051_pre.bak" "$2" "$3" <<'PY'
import json, sys
out, orig, exe, dv = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_GFX906_GDN_DOT2"] = dv
d["exe"] = exe
d["env"] = env
json.dump(d, open(out, "w", encoding="utf-8"), indent=2)
print("cfg %s exe=%s GDN_DOT2=%s env_n=%d" % (out, exe, dv, len(env)))
PY
}

restart() {
  bump RESTARTS
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

grab() { # $1 off lines prefix label
  local off=$1 label=$2
  local new
  new=$(tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log")
  local gpu dec
  gpu=$(echo "$new" | grep 'prefill timing:.*GPU timeline' | head -1)
  dec=$(echo "$new" | grep 'generated in' | tail -1)
  [ -n "$gpu" ] && echo "$label $gpu" >> "$W/phase_g2.txt" \
    || echo "$label MISSING_GPU_TIMELINE" >> "$W/phase_g2.txt"
  [ -n "$dec" ] && echo "$label $dec" >> "$W/phase_g2.txt" \
    || echo "$label MISSING_DECODE" >> "$W/phase_g2.txt"
}

perf_arm() { # $1 label, $2 exe, $3 dot2val
  log "=== G2 ARM $1 exe=$2 DOT2=$3 ==="
  mk_cfg "$CFG" "$2" "$3" || fail "mk_cfg"
  restart
  chat_uniq p2500.txt 8 "warm-$1-0" >/dev/null 2>&1 || true
  local n off
  for n in 1 2 3; do
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p2500.txt 16 "$1-2k5-$n" >>"$LOG" 2>&1 || fail "2k5 $n"
    grab "$off" "P2K5 $1 r$n"
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p8000.txt 16 "$1-8k-$n" >>"$LOG" 2>&1 || fail "8k $n"
    grab "$off" "P8K $1 r$n"
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_uniq p2500.txt 400 "$1-dec-$n" >>"$LOG" 2>&1 || fail "dec $n"
    grab "$off" "DEC $1 r$n"
  done
  log "=== G2 ARM $1 done ==="
}

echo "=== phase A: timing ==="
: > "$W/phase_g2.txt"
perf_arm a_off /data/bin/strata-0.1.57-r114 0
perf_arm b_on /data/bin/strata-0.1.57-r114 1

echo "=== phase B: numeric dumps (service stopped) ==="
bump STOPWINDOWS
docker stop -t 25 "$C" >/dev/null 2>&1 || true
sleep 2
mk_cfg "$W/cfg_g0.json" /data/bin/strata-0.1.57-r114 0 || fail "cfg_g0"
mk_cfg "$W/cfg_g1.json" /data/bin/strata-0.1.57-r114 1 || fail "cfg_g1"
cp -f "$W/cfg_w1051_pre.bak" "$W/cfg_hc.json" || fail "cfg_hc"

run_dump() { # $1 tag, $2 cfg
  log "=== DUMP $1 ==="
  docker run --rm --name "q51_$1" --device=/dev/kfd --device=/dev/dri \
    -v "$S/data":/data -v /models:/models -v "$S/pr/k10":/src -v "$W":/w "$IMG" \
    bash -lc "timeout 1800 python3 /w/qq_long.py prompt --config /w/$2 --out /w/L_$1 --ids /w/set32k_v2.ids.json --gpu-experts" \
    >>"$LOG" 2>&1
  local rc=$?
  log "DUMP $1 rc=$rc"
  [ "$rc" = 0 ] || fail "dump $1"
}

run_dump hc cfg_hc.json
run_dump g0 cfg_g0.json
run_dump g1 cfg_g1.json

echo "=== phase C: pcompare ==="
: > "$W/pcompare_g2.txt"
pcmp() { # $1 ref tag, $2 run tag
  docker run --rm -v "$W":/w "$IMG" \
    bash -lc "python3 /w/qq_long.py pcompare /w/L_$1 /w/L_$2" \
    | tee -a "$LOG" | sed "s/^/CMP $1 vs $2 /" >> "$W/pcompare_g2.txt"
}
pcmp g0 g1
pcmp hc g0
pcmp hc g1

echo "=== window done, restoring ==="
cat "$W/counter.txt" | tee -a "$LOG"
echo WINDOW_G2_DONE
