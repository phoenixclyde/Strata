#!/bin/bash
# W861-E: 零干扰采样器 —— 每秒记录 CPU 利用率 / GPU busy / 生产日志行号。
# 目的：decode 到底受限于 CPU 专家计算（AVX2）还是 GPU。只读 /proc 与 drm 节点，不碰引擎。
set -u
OUT=/home/albus/strata166/data/w861_sampler.tsv
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
DUR=${1:-1800}
: > "$OUT"
printf "ts\tuser\tsys\tidle\tiowait\tncpu\tgpu_busy\tgpu_power\tnlines\tcputot\n" >> "$OUT"
prev=""
end=$(( $(date +%s) + DUR ))
while [ "$(date +%s)" -lt "$end" ]; do
  cur=$(awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8, $2, $3, $4, $5}' /proc/stat)
  set -- $cur
  tot=$1; u=$2; s=$3; id=$4; iow=$5
  if [ -n "$prev" ]; then
    pprev=$prev
    du=$(( tot - pprev ))
    [ "$du" -le 0 ] && du=1
    pu=$(( (u - ${PREV_U:-0}) * 1000 / du ))
    ps=$(( (s - ${PREV_S:-0}) * 1000 / du ))
    pi=$(( (id - ${PREV_I:-0}) * 1000 / du ))
    pw=$(( (iow - ${PREV_W:-0}) * 1000 / du ))
  else
    pu=0; ps=0; pi=0; pw=0
  fi
  PREV_U=$u; PREV_S=$s; PREV_I=$id; PREV_W=$iow; prev=$tot
  gb=$(cat /sys/class/drm/card0/device/gpu_busy_percent 2>/dev/null || echo -1)
  gp=$(cat /sys/class/drm/card0/device/hwmon/hwmon*/power1_average 2>/dev/null | head -1 || echo -1)
  nl=$(wc -l < "$LOG" 2>/dev/null || echo 0)
  printf "%s\t%d\t%d\t%d\t%d\t%d\t%s\t%s\t%s\t%d\n" \
    "$(date +%H:%M:%S)" "$pu" "$ps" "$pi" "$pw" "$(nproc)" "$gb" "$gp" "$nl" "$tot" >> "$OUT"
  sleep 1
done
echo "sampler done: $(wc -l < "$OUT") lines"
