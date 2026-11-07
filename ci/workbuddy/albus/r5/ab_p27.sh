#!/bin/bash
# W805c KL 门：chunk 8192 (A) vs 16384 (B/C) —— 同一段 token 序列上的 teacher-forced KL
#   shape 轮 fresh ~10,000 token：chunk 8192 时 2 个 chunk（8192+1835），chunk 16384 时 1 个 chunk
#   probe 轮 fresh <= 300 => 走 verify 窗口 => STRATA_LOGPOS 落行
#   注意：两臂的 chunk 都 >= stream_all_min(3072) => share 不参与 => A 是确定性基线
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w805c_kl_$STAMP.txt
WANT_ENV=14          # 生产 12 + LOGPOS + LOGPOS_TOPK
SHORT_READ=300
cp "$CFG" /tmp/w805c_prod.json
restore_cfg() {
  cp /tmp/w805c_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W805c KL gate chunk 8192 vs 16384  $STAMP short_read=$SHORT_READ" > "$OUT"
python3 -c "import hashlib;b=open('kl_corpus3.json','rb').read();print('  corpus sha16=%s bytes=%d'%(hashlib.sha256(b).hexdigest()[:16],len(b)))" >> "$OUT"

setarm() {   # $1=arm
  python3 - "$CFG" "$1" "$SHORT_READ" <<'PY'
import json, sys
cfg, arm, sr = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_LOGPOS"] = "/data/w805_logpos_%s.tsv" % arm
e["STRATA_LOGPOS_TOPK"] = "64"
d["env"] = e
a = list(d.get("args") or [])
while "--prefill" in a:
    i = a.index("--prefill"); del a[i:i + 2]
while "--short-read" in a:
    i = a.index("--short-read"); del a[i:i + 2]
a += ["--prefill", "auto" if arm == "A" else "auto:16384", "--short-read", sr]
d["args"] = a
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
}

run() {
  local arm=$1
  rm -f "$DATA/w805_logpos_$arm.tsv"
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  local got chunk
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  chunk=$(grep -a "prompt chunk auto\|prompt path borrows" "$LOG" | tail -2 | tr "\n" " ")
  echo "  ENVCHECK want=$WANT_ENV got=${got:-?}" >> "$OUT"
  echo "  CHUNK ${chunk:-?}" >> "$OUT"
  if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got" >> "$OUT"; exit 1; fi
  python3 mt_kl.py kl_corpus3.json 8090 "$arm" "$DATA/w805c_$arm.json" >> "$OUT" 2>&1
  [ -f "$DATA/w805c_$arm.json" ] || { echo "!! ABORT no JSON" >> "$OUT"; exit 1; }
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
  if [ -f "$DATA/w805_logpos_$arm.tsv" ]; then
    echo "  LOGPOS rows=$(wc -l < "$DATA/w805_logpos_$arm.tsv")" >> "$OUT"
  else
    echo "  LOGPOS MISSING" >> "$OUT"
  fi
}

run A
run B
run C
echo "== DONE $OUT"
