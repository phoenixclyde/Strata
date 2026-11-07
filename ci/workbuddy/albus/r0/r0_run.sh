#!/bin/sh
# R0: 在 schedutil 下重建三档基线（阶段口径）。
# 自恢复：无论正常结束还是收到 HUP/INT/TERM，都会 cp 回原 config 并重启生产。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/r0_results_$TS.txt
BAK=$CFG.bak_r0_$TS
CONT=strata166-407
MODEL=qwen3.8-flash-next-ud-iq4_xs-abliterated

restore() {
  echo "=== RESTORE $(date +%H:%M:%S) ===" >> "$OUT"
  cp -f "$BAK" "$CFG" && echo "config restored from $BAK" >> "$OUT"
  md5sum "$CFG" >> "$OUT"
  docker restart "$CONT" >/dev/null 2>&1 && echo "container restarted" >> "$OUT"
  for i in $(seq 1 150); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  echo "governor_after=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)" >> "$OUT"
  echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK" && echo "backup=$BAK" >> "$OUT"
md5sum "$CFG" >> "$OUT"
echo "governor_before=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)" >> "$OUT"
echo "governor_all=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c | tr '\n' ' ')" >> "$OUT"

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
  if [ "$code" = "200" ]; then echo "warmup ok (try $i)" >> "$OUT"; break; fi
  echo "warmup http=$code (try $i)" >> "$OUT"
  sleep 6
done

prev_s=$(grep -a -c "decode GPU stages" "$LOG")
prev_t=$(grep -a -c "decode timing" "$LOG")

for tier in M M M S S L L; do
  echo "--- TIER $tier $(date +%H:%M:%S) ---" >> "$OUT"
  python3 /home/albus/strata166/tmp/w776_bench.py "$tier" 1 >> "$OUT" 2>&1
  now_s=$(grep -a -c "decode GPU stages" "$LOG")
  now_t=$(grep -a -c "decode timing" "$LOG")
  if [ "$now_s" -gt "$prev_s" ]; then
    grep -a "decode GPU stages" "$LOG" | tail -n +$((prev_s + 1)) >> "$OUT"
  fi
  if [ "$now_t" -gt "$prev_t" ]; then
    grep -a "decode timing" "$LOG" | tail -n +$((prev_t + 1)) >> "$OUT"
  fi
  prev_s=$now_s
  prev_t=$now_t
done

echo "ALL_TIERS_DONE $(date +%H:%M:%S)" >> "$OUT"
