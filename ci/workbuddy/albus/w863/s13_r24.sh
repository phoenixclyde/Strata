#!/bin/bash
# W863 · 补扫：R=2 全列，R=4 只列 1..4（R*NCOLS<=12）
set -u
O=/home/albus/w862_prod
OUT=/home/albus/strata166/w863/sweep_r24.txt
: > "$OUT"
for C in 1 2 3 4 5 6 7 8; do
  echo "#### cols=$C rows=2 ####" >> "$OUT"
  timeout 120 "$O/q8_prod_bench2" --iters 40 --bw 711 --cols $C --rows 2 --group single >> "$OUT" 2>&1
done
for C in 1 2 3 4; do
  echo "#### cols=$C rows=4 ####" >> "$OUT"
  timeout 120 "$O/q8_prod_bench2" --iters 40 --bw 711 --cols $C --rows 4 --group single >> "$OUT" 2>&1
done
echo "=== done $(wc -l < "$OUT") lines ==="
