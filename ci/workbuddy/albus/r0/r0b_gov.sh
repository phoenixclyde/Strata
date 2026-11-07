#!/bin/sh
# R0b: governor 交错 A/B（同一引擎进程内切换，不用重启引擎）。
# 顺序 perf, sched, perf, sched, perf, sched —— 同进程、同页缓存，差异只能来自 governor。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/r0b_gov_$TS.txt
BAK=$CFG.bak_r0b_$TS
CONT=strata166-407
MODEL=qwen3.8-flash-next-ud-iq4_xs-abliterated
GOVS=/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor

set_gov() {
  sudo -n sh -c "echo $1 | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null" 2>/dev/null
  now=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr '\n' ' ')
  echo "  gov_set=$1 actual=$now" >> "$OUT"
}

restore() {
  set_gov schedutil
  echo "=== RESTORE $(date +%H:%M:%S) ===" >> "$OUT"
  cp -f "$BAK" "$CFG" && echo "config restored" >> "$OUT"
  md5sum "$CFG" >> "$OUT"
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 150); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  echo "final_gov=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr '\n' ' ')" >> "$OUT"
  echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
}

echo "R0b START $(date +%Y-%m-%d_%H:%M:%S)" > "$OUT"
cp -f "$CFG" "$BAK"
md5sum "$CFG" >> "$OUT"
echo "gov_initial=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)" >> "$OUT"

python3 - "$CFG" >> "$OUT" 2>&1 <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d.setdefault('env', {})['STRATA_DECODE_TIMING'] = '1'
d['env']['STRATA_VERIFY_PROFILE'] = '1'
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('env_injected', d['env'])
PY

trap 'restore' EXIT HUP INT TERM

docker restart "$CONT" >/dev/null 2>&1
for i in $(seq 1 150); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
  sleep 1
done
sleep 25
for i in $(seq 1 12); do
  code=$(curl -s --max-time 30 -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8090/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"warm\"}],\"max_tokens\":4,\"temperature\":0}")
  [ "$code" = "200" ] && { echo "warmup ok" >> "$OUT"; break; }
  sleep 6
done

prev_s=$(grep -a -c "decode GPU stages" "$LOG")
prev_t=$(grep -a -c "decode timing" "$LOG")

# 先跑两次 M 让专家缓存进入稳态（丢弃）
for i in discard1 discard2; do
  echo "--- DISCARD $i $(date +%H:%M:%S) ---" >> "$OUT"
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  prev_s=$(grep -a -c "decode GPU stages" "$LOG")
  prev_t=$(grep -a -c "decode timing" "$LOG")
done

n=0
for gov in performance schedutil performance schedutil performance schedutil; do
  n=$((n + 1))
  set_gov "$gov"
  echo "--- ARM $n gov=$gov $(date +%H:%M:%S) ---" >> "$OUT"
  python3 /home/albus/strata166/tmp/w776_bench.py M 1 >> "$OUT" 2>&1
  now_s=$(grep -a -c "decode GPU stages" "$LOG")
  now_t=$(grep -a -c "decode timing" "$LOG")
  [ "$now_s" -gt "$prev_s" ] && grep -a "decode GPU stages" "$LOG" | tail -n +$((prev_s + 1)) >> "$OUT"
  [ "$now_t" -gt "$prev_t" ] && grep -a "decode timing" "$LOG" | tail -n +$((prev_t + 1)) >> "$OUT"
  prev_s=$now_s
  prev_t=$now_t
done

echo "ARMS_DONE $(date +%H:%M:%S)" >> "$OUT"
