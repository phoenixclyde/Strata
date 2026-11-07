#!/bin/bash
# 显存台阶取证：重启一次生产容器，1 s 采一次 VRAM + 引擎日志行号，把台阶对齐到日志行
L=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/tmp/vram_trace.csv
C0=$(wc -l < "$L")
echo "t,vram_used_b,logline,nstrata,nvision" > "$OUT"
T0=$(date +%s)
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 300); do
  t=$(( $(date +%s) - T0 ))
  v=$(cat /sys/class/drm/card0/device/mem_info_vram_used 2>/dev/null)
  ln=$(( $(wc -l < "$L") - C0 ))
  ns=$(pgrep -c -f "build-906/strata --serve" || true)
  nv=$(pgrep -c -f "strata-vision" || true)
  echo "$t,${v:-0},$ln,${ns:-0},${nv:-0}" >> "$OUT"
  curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "READY t=$t"; break; }
  sleep 1
done
echo "=== 采样结束，新增日志行（按到达顺序）"
tail -n +$((C0 + 1)) "$L" | grep -a -nE "engine started|memory guard|token embedding|native projection|draft layer loaded|expert arena|loaded 55|expert cache|borrows|VRAM free|session|KV" | cut -c1-150
