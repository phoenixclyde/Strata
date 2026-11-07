#!/bin/bash
# W804 KL 门（1-3K 段）：MAX=1024 vs MAX=3072 的 teacher-forced KL
#   shape 轮 fresh ~1830 => 落在 1024-3072：A 走 stream_all（不用 CPU），B/C 走 staged + share
#   probe 轮 fresh <= 300 => verify 窗口 => LOGPOS 落行
#   臂：A(MAX1024) B(MAX3072) C(MAX3072 第二遍)  —— A 是确定性基线（这段 share 不参与 => 无逐次浮动）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w804_kl2_$STAMP.txt
WANT_ENV=15
SHORT_READ=300
cp "$CFG" /tmp/w804_kl2_prod.json

echo "# W804 KL gate 1-3K  $STAMP short_read=$SHORT_READ" > "$OUT"
echo "  arms: A=auto/MAX1024  B=auto/MAX3072  C=auto/MAX3072(第二遍)" >> "$OUT"
python3 -c "import hashlib;b=open('kl_corpus2.json','rb').read();print('  corpus sha16=%s bytes=%d'%(hashlib.sha256(b).hexdigest()[:16],len(b)))" >> "$OUT"

setarm() {   # $1=arm
  python3 - "$CFG" "$1" "$SHORT_READ" <<'PY'
import json, sys
cfg, arm, sr = sys.argv[1], sys.argv[2], sys.argv[3]
mx = "1024" if arm == "A" else "3072"
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_CPU_SHARE"] = "auto"
e["STRATA_PREFILL_CPU_SHARE_MAX"] = mx
e["STRATA_LOGPOS"] = "/data/w804_logpos_%s.tsv" % arm
e["STRATA_LOGPOS_TOPK"] = "64"
e["STRATA_DBG_CPU_GATE"] = "1"
d["env"] = e
a = list(d.get("args") or [])
while "--short-read" in a:
    i = a.index("--short-read")
    del a[i:i + 2]
a += ["--short-read", sr]
d["args"] = a
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
}

run() {   # $1=arm $2=want
  local arm=$1 want=$2
  rm -f "$DATA/w804_logpos_$arm.tsv"
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  local got sh
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  sh=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_PREFILL_CPU_SHARE" | sort | tr "\n" " "' 2>/dev/null)
  echo "  ENVCHECK want=$want got=${got:-?} :: ${sh:-?}" >> "$OUT"
  if [ "${got:-0}" != "$want" ]; then echo "!! ABORT env_n $got != $want" >> "$OUT"; echo ABORT; exit 1; fi
  python3 mt_kl.py kl_corpus2.json 8090 "$arm" "$DATA/w804_kl2_$arm.json" >> "$OUT" 2>&1
  if [ ! -f "$DATA/w804_kl2_$arm.json" ]; then echo "!! ABORT no JSON $arm" >> "$OUT"; echo ABORT; exit 1; fi
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
  echo "  cpu_gate_share_lines=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -ac 'cpu gate:.*-> share')" >> "$OUT"
  if [ -f "$DATA/w804_logpos_$arm.tsv" ]; then
    echo "  LOGPOS rows=$(wc -l < "$DATA/w804_logpos_$arm.tsv") bytes=$(stat -c%s "$DATA/w804_logpos_$arm.tsv")" >> "$OUT"
  else
    echo "  LOGPOS MISSING" >> "$OUT"
  fi
}

run A 15
run B 15
run C 15

cp /tmp/w804_kl2_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d share=%s max=%s sr=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE'),d['env'].get('STRATA_PREFILL_CPU_SHARE_MAX'),('--short-read' in d['args'])))" >> "$OUT"
echo "== DONE $OUT"
