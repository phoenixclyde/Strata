#!/bin/bash
# W1051d: decode determinism control for the G2c text flips.
# Same prompt P ("g2c-pair-1"), arm a_off (DOT2=0):
#   req1 cold (after restart)          -> T1
#   req2 same session (cache hit)      -> T2  (decode-only determinism from same KV)
#   restart, req3 cold again           -> T3  (full pipeline determinism)
# then arm b_on (DOT2=1):
#   req4 cold                          -> T4
# If T1==T2==T3, decode is deterministic and cross-arm flips are kernel-caused.
set -u
C=strata166-407
S=/home/albus/strata166
W=$S/tmp/w1051
CFG=$S/data/strata-huihui-ud-iq4_xs.json
LOG=$W/window_g2d.log
mkdir -p "$W"
: > "$LOG"
cp -f "$CFG" "$W/cfg_g2d_pre.bak" || exit 1

log() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }
fail() { log "FAIL: $*"; exit 1; }

restore() {
  cp -f "$W/cfg_g2d_pre.bak" "$CFG" || true
  docker start "$C" >/dev/null 2>&1 || true
  for i in $(seq 1 90); do
    st=$(curl -s -m 3 localhost:8090/health 2>/dev/null | head -c 24 || true)
    if echo "$st" | grep -q ok; then log "RESTORE: health ok after ${i}s"; return 0; fi
    sleep 1
  done
  log "RESTORE FAIL"; return 1
}
trap restore EXIT INT TERM

mk_cfg() {
  python3 - "$CFG" "$W/cfg_g2d_pre.bak" "$1" "$2" <<'PY'
import json, sys
live, orig, exe, dv = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = json.load(open(orig, encoding="utf-8-sig"))
env = dict(d.get("env") or {})
env["STRATA_GFX906_GDN_DOT2"] = dv
d["exe"] = exe; d["env"] = env
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

chat_gen() {
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

P="g2c-pair-1"
log "=== G2D arm a_off DOT2=0 ==="
mk_cfg /data/bin/strata-0.1.57-r114 0 || fail "cfg"
restart
chat_gen "$P" 600 "$W/ctrl_T1.txt" >>"$LOG" 2>&1 || fail T1
chat_gen "$P" 600 "$W/ctrl_T2.txt" >>"$LOG" 2>&1 || fail T2
restart
chat_gen "$P" 600 "$W/ctrl_T3.txt" >>"$LOG" 2>&1 || fail T3
log "=== G2D arm b_on DOT2=1 ==="
mk_cfg /data/bin/strata-0.1.57-r114 1 || fail "cfg"
restart
chat_gen "$P" 600 "$W/ctrl_T4.txt" >>"$LOG" 2>&1 || fail T4

python3 - "$W" <<'PY' | tee -a "$LOG"
import io, sys
W = sys.argv[1]
def load(n):
    return io.open("%s/ctrl_%s.txt" % (W, n), encoding="utf-8").read()
def dcmp(a, b, la, lb):
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    same = (i == min(len(a), len(b)) and len(a) == len(b))
    print("%s vs %s: %s (diverge at %d, lens %d/%d)" % (
        la, lb, "IDENTICAL" if same else "DIVERGE", i, len(a), len(b)))
T = {n: load(n) for n in ("T1", "T2", "T3", "T4")}
dcmp(T["T1"], T["T2"], "T1", "T2")
dcmp(T["T1"], T["T3"], "T1", "T3")
dcmp(T["T2"], T["T3"], "T2", "T3")
dcmp(T["T1"], T["T4"], "T1", "T4")
PY
echo WINDOW_G2D_DONE | tee -a "$LOG"
