#!/bin/bash
set -u
LOG=/data/strata-huihui-ud-iq4_xs.log
echo "=== 提取 (tokens, qsa attn ms, %) ==="
docker exec strata166-407 sh -c "
  grep -oE 'strata prefill timing: [0-9]+ tokens[^:]*: .*qsa attn [0-9]+ \([0-9.]+%\)' $LOG \
  | sed -E 's/strata prefill timing: ([0-9]+) tokens.*qsa attn ([0-9]+) \(([0-9.]+)%\).*/\1 \2 \3/' \
  | sort -n -u | tail -25
"

echo
echo "=== 同样提取 qsa proj（对照：它应是 O(L)）==="
docker exec strata166-407 sh -c "
  grep -oE 'strata prefill timing: [0-9]+ tokens.*qsa proj [0-9]+ \([0-9.]+%\)' $LOG \
  | sed -E 's/strata prefill timing: ([0-9]+) tokens.*qsa proj ([0-9]+) \(([0-9.]+)%\).*/\1 \2 \3/' \
  | sort -n -u | tail -12
"
