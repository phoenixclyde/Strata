#!/bin/bash
# W804 追加两臂，同一个 read 扫描（与 A/B/C 完全同尺寸、同语料、同仪器）
#   D = share 0 + STRATA_PREFILL_STREAM_MIN=3072   -> 只改 staged 阈值、不用 CPU
#       （拆混淆：B 在 1-3K 的收益到底来自「CPU 参与」还是来自「改成 staged」）
#       cpu_share_max() 只在 share_on 时才被当作 g_stream_min_share，所以必须直接给 STREAM_MIN
#   E = share auto + MAX=4096 -> 看收益在 3K 以上还延不延伸
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w804_read2_$STAMP.txt
SIZES=150,300,600,900,1500,2500
REPS=3
cp "$CFG" /tmp/w804b_prod.json

echo "# W804b isolation arms $STAMP sizes=$SIZES reps=$REPS" > "$OUT"
echo "  D = share 0 + STREAM_MIN 3072（staging-only）; E = auto + MAX 4096" >> "$OUT"

setarm() {
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
e = dict(d.get("env") or {})
for k in ("STRATA_PREFILL_STREAM_MIN",):
    e.pop(k, None)
e["STRATA_PREFILL_TIMING"] = "1"
e["STRATA_TRACE"] = "1"
e["STRATA_DBG_CPU_GATE"] = "1"
if arm == "D":
    e["STRATA_PREFILL_CPU_SHARE"] = "0"
    e["STRATA_PREFILL_CPU_SHARE_MAX"] = "1024"
    e["STRATA_PREFILL_STREAM_MIN"] = "3072"
else:
    e["STRATA_PREFILL_CPU_SHARE"] = "auto"
    e["STRATA_PREFILL_CPU_SHARE_MAX"] = "4096"
d["env"] = e
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
}

run() {
  local arm=$1 want=$2
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  local got
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  local sh
  sh=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); tr "\0" "\n" < /proc/$p/environ | grep -E "^STRATA_PREFILL_(CPU_SHARE|STREAM_MIN)" | sort | tr "\n" " "' 2>/dev/null)
  echo "  ENVCHECK want=$want got=${got:-?} :: ${sh:-?}" >> "$OUT"
  if [ "${got:-0}" != "$want" ]; then echo "!! ABORT env_n $got != $want" >> "$OUT"; echo ABORT; exit 1; fi
  python3 mt_read.py 8090 "$arm" "$DATA/w804_read_$arm.json" "$SIZES" "$REPS" kl_pool.json >> "$OUT" 2>&1
  if [ ! -f "$DATA/w804_read_$arm.json" ]; then echo "!! ABORT no JSON" >> "$OUT"; echo ABORT; exit 1; fi
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
  echo "  cpu_gate_share_lines=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -ac 'cpu gate:.*-> share')" >> "$OUT"
}

run D 16
run E 15

cp /tmp/w804b_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d share=%s max=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE'),d['env'].get('STRATA_PREFILL_CPU_SHARE_MAX')))" >> "$OUT"
echo "== DONE $OUT"
