#!/bin/bash
# W803: STRATA_PREFILL_CPU_SHARE 的 teacher-forced KL 质量门（四臂：A=0 B=auto C=0 D=auto）
#   依据：W767（LOGPOS 原生探针，self=0 读数下限）+ W800（cpu_share 只在 staged 的 prefill chunk 生效）
#         + 上游 #2685 的 RTX 4070S 报告（share 让 prefill 逐次不同 => 必须有「同臂重复」臂做底噪）
#   注入靠 shape 轮（fresh ∈ (short_read,1024) => 走 staged batched prefill => cpu_share 生效）
#   测量靠 probe 轮（fresh <= short_read => 走 verify 窗口 => LOGPOS 落行）
#   用法：ab_p21.sh probe   # 只跑 B 臂 + 前 4 轮，验证协议
#         ab_p21.sh full    # A B C D
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
MODE=${1:-full}
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w803_kl_$STAMP.txt
WANT_ENV=14
SHORT_READ=300
cp "$CFG" /tmp/w803_prod.json

echo "# W803 KL gate mode=$MODE $STAMP short_read=$SHORT_READ" > "$OUT"
case "$MODE" in
  probe) echo "  order: B" >> "$OUT" ;;
  extra) echo "  order: E(auto) F(auto)" >> "$OUT" ;;
  *)     echo "  order: A(0) B(auto) C(0) D(auto)" >> "$OUT" ;;
esac
python3 -c "import json,hashlib;d=json.load(open('$CFG'));print('start env_n=%d args_n=%d'%(len(d['env']),len(d['args'])))" >> "$OUT"
python3 -c "import hashlib;b=open('kl_corpus.json','rb').read();print('  corpus sha16=%s bytes=%d'%(hashlib.sha256(b).hexdigest()[:16],len(b)))" >> "$OUT"

setarm() {   # $1=arm  $2=share
  python3 - "$CFG" "$2" "$1" "$SHORT_READ" <<'PY'
import json, sys
cfg, share, tag, sr = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_CPU_SHARE"] = share
e["STRATA_LOGPOS"] = "/data/w803_logpos_%s.tsv" % tag
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

run() {   # $1=arm $2=share $3=corpus
  local arm=$1 share=$2 corpus=$3
  rm -f "$DATA/w803_logpos_$arm.tsv"
  setarm "$arm" "$share"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm share=$share ready=${ok}s corpus=$corpus" >> "$OUT"
  local got
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  local sh
  sh=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); tr "\0" "\n" < /proc/$p/environ | grep "^STRATA_PREFILL_CPU_SHARE="' 2>/dev/null)
  echo "  ENVCHECK want=$WANT_ENV got=${got:-?} ${sh:-share=?}" >> "$OUT"
  if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got != $WANT_ENV" >> "$OUT"; echo "ABORT"; exit 1; fi
  python3 mt_kl.py "$corpus" 8090 "$arm" "$DATA/w803_kl_$arm.json" >> "$OUT" 2>&1
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
  echo "  cpu_gate_share_lines=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -ac 'cpu gate:.*-> share')" >> "$OUT"
  if [ -f "$DATA/w803_logpos_$arm.tsv" ]; then
    echo "  LOGPOS rows=$(wc -l < "$DATA/w803_logpos_$arm.tsv") bytes=$(stat -c%s "$DATA/w803_logpos_$arm.tsv")" >> "$OUT"
  else
    echo "  LOGPOS MISSING" >> "$OUT"
  fi
}

if [ "$MODE" = probe ]; then
  run B auto kl_probe.json
elif [ "$MODE" = extra ]; then
  # 追加两个「开 share」样本：给 B||D 这个单样本一个可比的分布（on-vs-on 的 n=1 是决策的瓶颈）
  run E auto kl_corpus.json
  run F auto kl_corpus.json
else
  run A 0    kl_corpus.json
  run B auto kl_corpus.json
  run C 0    kl_corpus.json
  run D auto kl_corpus.json
fi

cp /tmp/w803_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d share=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE')))" >> "$OUT"
echo "== DONE $OUT"
