#!/bin/bash
# W863 · 重启到 0.1.55h 并验证
set -u
D=/home/albus/strata166/data/bin
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
echo "=== symbol check (BRE alternation, escaped) ==="
for f in "$D/strata-0.1.55h" "$D/strata-0.1.55g"; do
  echo "$(basename $f): sym=$(nm -C "$f" 2>/dev/null | grep -c 'wave_rows_for\|kWaveRows') env=$(strings -a "$f" | grep -c STRATA_MMVQ_WAVE_ROWS)"
done
echo "=== restart ==="
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then echo "health after ${i}s"; break; fi
  sleep 1
done
sleep 8
curl -s --max-time 6 http://127.0.0.1:8090/health; echo
echo "=== engine line ==="
grep -a "engine started" "$LOG" | tail -1 | cut -c1-160
echo "=== startup accounting ==="
grep -a -E "native projection matrices|HC_Q8|window up to|VRAM free with everything|loaded .* GiB at" "$LOG" | tail -4 | cut -c1-150
echo "=== VRAM ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep Used
