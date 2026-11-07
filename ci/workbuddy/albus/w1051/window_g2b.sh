#!/bin/bash
# W1051b: decode-side G2 for STRATA_GFX906_GDN_DOT2 on r114.
# (a) decode speed n=6 cold 600-token greedy runs per arm (unique nonces);
# (b) decode text check: SAME fixed prompt, one cold run per arm right after a
#     restart -- validity self-proved by usage.cached_tokens == 0 (a persistent
#     cache would make the b run hit a's KV and is flagged TEXT_CHECK_INVALID).
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1051
IMG=strata-gfx906:0.2.11-101
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_g2b.log
mkdir -p "$W"
: > "$LOG"
cp -f "$CFG" "$W/cfg_g2b_pre.bak" || exit 1
echo "RESTARTS=0" > "$W/counter_g2b.txt"

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

bump() {
  python3 - "$W/counter_g2b.txt" "$1" <<'PY'
import io, sys
p, key = sys.argv[1], sys.argv[2]
d = dict(l.split("=", 1) for l in io.open(p).read().split() if "=" in l)
d[key] = str(int(d.get(key, "0")) + 1)
io.open(p, "w", newline="\n").write(" ".join("%s=%s" % (k, v) for k, v in d.items()))
print("counter", key, d[key])
PY
}

restore() {
  cp -f "$W/cfg_g2b_pre.bak" "$CFG" || true
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

mk_cfg() { # $1 exe, $2 gdn_dot2
  python3 - "$CFG" "$W/cfg_g2b_pre.bak" "$1" "$2" <<'PY'
import json, sys
live, orig, exe, dv = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_GFX906_GDN_DOT2"] = dv
d["exe"] = exe
d["env"] = env
json.dump(d, open(live, "w", encoding="utf-8"), indent=2)
print("cfg exe=%s GDN_DOT2=%s" % (exe, dv))
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

chat_gen() { # $1 nonce-suffix, $2 max_tokens, $3 out-text-file
  python3 - "$W/p2500.txt" "$1" "$2" "$3" <<'PY'
import json, sys, urllib.request
txt = open(sys.argv[1], encoding="utf-8").read() + " " + sys.argv[2]
body = json.dumps({"model": "strata", "messages": [{"role": "user", "content": txt}],
                   "max_tokens": int(sys.argv[3]), "temperature": 0}).encode()
req = urllib.request.Request("http://localhost:8090/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=3600) as r:
    d = json.loads(r.read())
u = d.get("usage") or {}
txt_out = d["choices"][0]["message"]["content"]
open(sys.argv[4], "w", encoding="utf-8").write(txt_out)
print("usage", u, "textlen", len(txt_out))
PY
}

grab_dec() { # $1 off, $2 label
  tail -n +"$1" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'generated in' | tail -1 \
    | sed "s/^/$2 /" >> "$W/decode_g2b.txt" \
    || echo "$2 MISSING_DECODE" >> "$W/decode_g2b.txt"
}

: > "$W/decode_g2b.txt"

for arm in a_off b_on; do
  if [ "$arm" = a_off ]; then val=0; else val=1; fi
  log "=== G2B ARM $arm DOT2=$val ==="
  mk_cfg /data/bin/strata-0.1.57-r114 "$val" || fail "mk_cfg"
  restart
  # (b) text check: fixed prompt, cold (first request after restart)
  log "--- text check $arm ---"
  chat_gen "g2-textcheck-fixed-1" 600 "$W/text_$arm.txt" >>"$LOG" 2>&1 || fail "text $arm"
  # (a) speed: n=6 cold unique-prompt 600-token runs
  for n in 1 2 3 4 5 6; do
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_gen "$arm-speed-$n-$(date +%s)" 600 "$W/spd_${arm}_$n.txt" >>"$LOG" 2>&1 || fail "speed $n"
    grab_dec "$off" "DEC600 $arm r$n"
  done
  log "=== G2B ARM $arm done ==="
done

log "=== text diff ==="
if cmp -s "$W/text_a_off.txt" "$W/text_b_on.txt"; then
  log "TEXT_IDENTICAL"
else
  python3 - "$W/text_a_off.txt" "$W/text_b_on.txt" <<'PY'
import sys
a = open(sys.argv[1], encoding="utf-8").read()
b = open(sys.argv[2], encoding="utf-8").read()
i = 0
while i < min(len(a), len(b)) and a[i] == b[i]:
    i += 1
print("TEXT_DIVERGE at %d/%d,%d (a_len=%d b_len=%d)" % (i, len(a), len(b), len(a), len(b)))
print("a_tail:", repr(a[max(0, i - 20):i + 40]))
print("b_tail:", repr(b[max(0, i - 20):i + 40]))
PY
fi
cat "$W/counter_g2b.txt" | tee -a "$LOG"
echo WINDOW_G2B_DONE
