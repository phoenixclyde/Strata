#!/bin/bash
# W805：把相位账补到真实使用的 chunk（8192）+ 三档对照（2K / 4K / 8K）
#   只跑一个臂：生产配置（auto + MAX3072）+ 仪表（TIMING / TRACE / DBG_CPU_GATE）
#   目的：W804 的相位数据只到 2196 token（那一档已经 < stream_all_min=3072 => 走 staged），
#         而真机上的 36k prompt 是 8192 的 chunk（>= 3072 => stream_all，share 完全不参与）=> 相位结构不同。
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w805_phase_$STAMP.txt
SIZES=2000,4000,8000
REPS=2
WANT_ENV=15
cp "$CFG" /tmp/w805_prod.json
restore_cfg() {
  cp /tmp/w805_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W805 phase account sizes=$SIZES reps=$REPS $STAMP" > "$OUT"
python3 - "$CFG" <<'PY'
import json, sys
cfg = sys.argv[1]
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_TIMING"] = "1"
e["STRATA_TRACE"] = "1"
e["STRATA_DBG_CPU_GATE"] = "1"
d["env"] = e
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
docker restart strata166-407 >/dev/null 2>&1
ok=0
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
mark "$OUT"
echo "=== ARM P ready=${ok}s" >> "$OUT"
got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
echo "  ENVCHECK want=$WANT_ENV got=${got:-?}" >> "$OUT"
if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got" >> "$OUT"; exit 1; fi
python3 mt_read.py 8090 P "$DATA/w805_read_P.json" "$SIZES" "$REPS" kl_pool.json >> "$OUT" 2>&1
[ -f "$DATA/w805_read_P.json" ] || { echo "!! ABORT no JSON" >> "$OUT"; exit 1; }
slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "^strata prefill timing: host:" | sed 's/^/  PH /' >> "$OUT"
echo "  cpu_gate_share_lines=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -ac 'cpu gate:.*-> share')" >> "$OUT"
echo "== DONE $OUT"
