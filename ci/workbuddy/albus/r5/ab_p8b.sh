#!/bin/sh
# W798b：decode 基准的可重复性 + 漂移归因
#
# 为什么：W798 的五臂结果全部"比 A 慢"，而 A 是**第一个**跑的（A 的 r5/r6 decode_ms 3,483/3,198，
# 其余四臂都在 3,600-4,400）。这更像位置效应而不是臂效应 —— 若如此，那四臂结论全部作废。
#
# 做法：同一 env（生产 10 项）连跑三次，每次 restart，每次前后采 sclk / edge 温度 / 封装功耗。
#   - 若三次单调变慢 => 全局漂移（热/功耗），decode 端到端不可判，必须换相位或加冷却
#   - 若三次在 ±5% 内摆动 => W798 的五臂可判，A 的"快"是臂效应以外的偶然
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
OUT=/home/albus/strata166/data/w798b_rep_$TS.txt
CONT=strata166-407
OKFLAG=/tmp/w798b_done
rm -f "$OKFLAG"

sensor() {
  /opt/rocm/bin/rocm-smi --showclocks --showtemp --showpower 2>/dev/null | \
    grep -E "sclk clock level|mclk clock level|Sensor edge|Sensor junction|Socket Graphics" | \
    tr '\n' ' ' | sed 's/GPU\[0\][[:space:]]*:[[:space:]]*//g' >> "$OUT"
  echo "" >> "$OUT"
}

restart_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 300); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 6
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restore $(date +%H:%M:%S) ===" >> "$OUT"
    restart_up
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
echo "env=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
trap 'keepup' EXIT HUP INT TERM

for rep in 1 2 3; do
  echo "=== REP $rep $(date +%H:%M:%S) ===" >> "$OUT"
  restart_up
  echo -n "sensor_before: " >> "$OUT"; sensor
  python3 /home/albus/strata166/tmp/mt_decode2.py >> "$OUT" 2>&1
  echo -n "sensor_after: " >> "$OUT"; sensor
done

echo "=== DONE $(date +%H:%M:%S) ===" >> "$OUT"
touch "$OKFLAG"
