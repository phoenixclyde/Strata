#!/bin/sh
# R5-prefill: 取 prefill 分相位账（STRATA_PREFILL_TIMING=1），M x4 + L x1。
# 自恢复：任何退出路径都 cp 回原 config 并重启生产（纪律⑥ 远端 detached）。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/data/r5_pf_$TS.txt
BAK=$CFG.bak_r5pf_$TS
CONT=strata166-407
MODEL=qwen3.8-flash-next-ud-iq4_xs-abliterated

restore() {
  echo "=== RESTORE $(date +%H:%M:%S) ===" >> "$OUT"
  cp -f "$BAK" "$CFG" && echo "config restored from $BAK" >> "$OUT"
  md5sum "$CFG" >> "$OUT"
  docker restart "$CONT" >/dev/null 2>&1 && echo "container restarted" >> "$OUT"
  for i in $(seq 1 200); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "prod ready ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  curl -s --max-time 5 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('after slots',e['expert_slots'],'vram',e['vram_free_mib'],'ver',e['version'])" >> "$OUT" 2>&1
  echo "env_after=$(python3 -c "import json;print(json.load(open('$CFG')).get('env'))")" >> "$OUT"
  echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
}

echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
cp -f "$CFG" "$BAK" && echo "backup=$BAK" >> "$OUT"
md5sum "$CFG" >> "$OUT"
echo "governor=$(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c | tr '\n' ' ')" >> "$OUT"

python3 - "$CFG" >> "$OUT" 2>&1 <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d.setdefault('env', {})['STRATA_PREFILL_TIMING'] = '1'
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('env_injected', sorted(d['env'].items()))
PY

trap 'restore' EXIT HUP INT TERM

docker restart "$CONT" >/dev/null 2>&1
for i in $(seq 1 200); do
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
  sleep 1
done
sleep 25

prev=$(grep -a -c "strata prefill timing" "$LOG")

for tier in M M M M L; do
  echo "--- TIER $tier $(date +%H:%M:%S) ---" >> "$OUT"
  python3 /home/albus/strata166/tmp/w776_bench.py "$tier" 1 >> "$OUT" 2>&1
  now=$(grep -a -c "strata prefill timing" "$LOG")
  if [ "$now" -gt "$prev" ]; then
    grep -a "strata prefill timing" "$LOG" | tail -n +$((prev + 1)) >> "$OUT"
  fi
  prev=$now
done

echo "DONE $(date +%H:%M:%S)" >> "$OUT"
