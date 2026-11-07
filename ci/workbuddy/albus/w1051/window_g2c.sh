#!/bin/bash
# W1051c: paired decode A/B for STRATA_GFX906_GDN_DOT2 on r114.
# Same N nonces run under both arms (cache does not survive restart -- proven
# by cached_tokens=0 on the g2b text check), so spec-decode draft acceptance
# noise cancels pairwise.  n=8 pairs x 600 tokens.  Also accumulates 8 more
# text pairs for the decode-numeric flip count.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1051
IMG=strata-gfx906:0.2.11-101
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_g2c.log
mkdir -p "$W/pair"
: > "$LOG"
cp -f "$CFG" "$W/cfg_g2c_pre.bak" || exit 1

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  cp -f "$W/cfg_g2c_pre.bak" "$CFG" || true
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
  python3 - "$CFG" "$W/cfg_g2c_pre.bak" "$1" "$2" <<'PY'
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

chat_gen() { # $1 suffix, $2 max_tokens, $3 out-text-file
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
ch = (d.get("choices") or [{}])[0]
msg = ch.get("message") or {}
txt_out = msg.get("content") or msg.get("reasoning_content") or ch.get("text") or ""
if not isinstance(txt_out, str):
    txt_out = json.dumps(txt_out, ensure_ascii=False)
open(sys.argv[4], "w", encoding="utf-8").write(txt_out)
print("usage", u, "textlen", len(txt_out))
PY
}

: > "$W/decode_g2c.txt"
N=8
for arm in a_off b_on; do
  if [ "$arm" = a_off ]; then val=0; else val=1; fi
  log "=== G2C ARM $arm DOT2=$val ==="
  mk_cfg /data/bin/strata-0.1.57-r114 "$val" || fail "mk_cfg"
  restart
  for n in $(seq 1 $N); do
    off=$(wc -l < "$S/data/strata-huihui-ud-iq4_xs.log")
    chat_gen "g2c-pair-$n" 600 "$W/pair/${arm}_$n.txt" >>"$LOG" 2>&1 || fail "pair $n"
    tail -n +"$off" "$S/data/strata-huihui-ud-iq4_xs.log" | grep 'generated in' | tail -1 \
      | sed "s/^/DEC600 $arm p$n /" >> "$W/decode_g2c.txt" \
      || echo "DEC600 $arm p$n MISSING" >> "$W/decode_g2c.txt"
  done
  log "=== G2C ARM $arm done ==="
done
log "=== paired text flips ==="
python3 - "$W" <<'PY' | tee -a "$LOG"
import io, sys
W = sys.argv[1]
flips = 0
for n in range(1, 9):
    a = io.open("%s/pair/a_off_%d.txt" % (W, n), encoding="utf-8").read()
    b = io.open("%s/pair/b_on_%d.txt" % (W, n), encoding="utf-8").read()
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    same = (i == min(len(a), len(b)) and len(a) == len(b))
    if same:
        print("pair %d IDENTICAL len=%d" % (n, len(a)))
    else:
        flips += 1
        print("pair %d DIVERGE at %d (a=%d b=%d)" % (n, i, len(a), len(b)))
print("FLIPS %d of 8" % flips)
PY
echo WINDOW_G2C_DONE | tee -a "$LOG"
