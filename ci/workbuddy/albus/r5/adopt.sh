#!/bin/sh
# W792 落生产：先做 FP16 上溢范围检查（临时 F16_RANGE），再装 gen_config 产出的最终 config。
# 自恢复：若最终装填未完成（无 FINAL_OK 标记），退出时一律 cp 回备份并重启。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
NEW=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json.w792final
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/w792_adopt_$TS.txt
BAK=$CFG.bak_w792_$TS
CONT=strata166-407
DONE_FLAG=/tmp/w792_final_ok

rm -f "$DONE_FLAG"

restore() {
  if [ ! -f "$DONE_FLAG" ]; then
    echo "=== ROLLBACK $(date +%H:%M:%S) ===" >> "$OUT"
    cp -f "$BAK" "$CFG" && echo "config rolled back" >> "$OUT"
    docker restart "$CONT" >/dev/null 2>&1
    for i in $(seq 1 200); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
      sleep 1
    done
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

wait_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 200); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 20
}

echo "START $(date +%Y-%m-%d_%H:%M:%S)" > "$OUT"
cp -f "$CFG" "$BAK"
echo "bak=$BAK" >> "$OUT"
md5sum "$BAK" >> "$OUT"
echo "env_before=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"

trap 'restore' EXIT HUP INT TERM

# ---- A：上溢范围检查（临时加 F16_RANGE + PREFILL_TIMING）
echo "=== A range check $(date +%H:%M:%S) ===" >> "$OUT"
python3 - "$NEW" "$CFG" >> "$OUT" 2>&1 <<'PY'
import json, sys
new, cfg = sys.argv[1], sys.argv[2]
d = json.load(open(new))
d.setdefault('env', {})['STRATA_F16_RANGE'] = '1'
d['env']['STRATA_PREFILL_TIMING'] = '1'
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('range env', sorted(d['env'].items()))
PY
wait_up
prev=$(grep -a -c "strata f16 range" "$LOG")
python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
now=$(grep -a -c "strata f16 range" "$LOG")
if [ "$now" -gt "$prev" ]; then grep -a "strata f16 range" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"; fi
grep -a "FP16 in and out" "$LOG" | tail -1 >> "$OUT"
grep -a "21822 tokens" "$LOG" | tail -1 >> "$OUT"

# ---- B：装最终 config
echo "=== B install final $(date +%H:%M:%S) ===" >> "$OUT"
cp -f "$NEW" "$CFG" && echo "final installed" >> "$OUT"
md5sum "$CFG" >> "$OUT"
wait_up
echo "env_after=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
curl -s --max-time 6 http://127.0.0.1:8090/health >> "$OUT"; echo >> "$OUT"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
echo "governor=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c | tr '\n' ' ')" >> "$OUT"
touch "$DONE_FLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
