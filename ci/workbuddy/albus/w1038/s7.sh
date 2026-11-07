#!/bin/bash
S=/home/albus/strata166/pr/k10
echo "=== A. kv-q4 bench 目录 ==="
ls -la $S/bench/results/2026-09-27-kv-q4/ 2>/dev/null
echo
echo "=== B. 里面的摘要 ==="
for f in $S/bench/results/2026-09-27-kv-q4/*.md $S/bench/results/2026-09-27-kv-q4/*.json; do
  [ -f "$f" ] || continue
  echo "--- $f"
  head -c 4000 "$f"
  echo
done
echo
echo "=== C. int8 read bench ==="
ls -la $S/bench/results/2026-10-03-v100-kv-int8-read/ 2>/dev/null
