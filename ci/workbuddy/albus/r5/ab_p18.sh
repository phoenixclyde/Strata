#!/bin/bash
# W802c：CPU share 采纳门 —— 无仪器（不开 PREFILL_TIMING/TRACE），2 臂 x 2 rep，顺序 A B B A
#   每臂：restart -> envcheck -> parity(固定问题 48 tok，落盘正文) -> chat bench(4 轮) -> M x1
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w802c_gate_$STAMP.txt
cp "$CFG" "$CFG.bak_w802c_$STAMP"
cp "$CFG" /tmp/w802c_prod.json
echo "# W802c cpu_share 采纳门  $STAMP  order=A(0) B(auto) B A   无仪器" > "$OUT"

setcs() {
  cp /tmp/w802c_prod.json "$CFG"
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, val = sys.argv[1], sys.argv[2]
d = json.load(open(cfg)); e = d.setdefault("env", {})
e["STRATA_PREFILL_CPU_SHARE"] = val
for k in ("STRATA_PREFILL_TIMING", "STRATA_TRACE"): e.pop(k, None)
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  setcs share=%s env_n=%d" % (val, len(e)))
PY
}

run() {
  local val=$1 arm=$2 rep=$3
  setcs "$val"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm share=$val rep $rep ready=${ok}s" >> "$OUT"
  local got
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  echo "  ENVCHECK got=${got:-?} (want 10，无 TIMING)" >> "$OUT"
  python3 mt_gate.py "$arm$rep" >> "$OUT" 2>&1
  python3 w776_bench.py M 1 >> "$OUT" 2>&1
}

run 0    A 1
run auto B 1
run auto B 2
run 0    A 2

cp /tmp/w802c_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
