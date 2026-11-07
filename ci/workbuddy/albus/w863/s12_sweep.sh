#!/bin/bash
# W863 · R 表实测化：ncols 1..8 × (R=1 | R=table)，真实 kernel + 生产 flags
# 只读生产库，不动进程。输出落文件供解析。
set -u
O=/home/albus/w862_prod
OUT=/home/albus/strata166/w863/sweep_cols.txt
mkdir -p /home/albus/strata166/w863
: > "$OUT"
echo "=== free VRAM before ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep -i "used\|total" | head -4
for C in 1 2 3 4 5 6 7 8; do
  for RW in 1 0; do
    echo "#### cols=$C rows=$RW ####" >> "$OUT"
    timeout 120 "$O/q8_prod_bench2" --iters 40 --bw 711 --cols $C --rows $RW --group single >> "$OUT" 2>&1
  done
done
echo "=== done, lines: $(wc -l < "$OUT") ==="
echo "=== free VRAM after ==="
rocm-smi --showmeminfo vram 2>/dev/null | grep -i "used\|total" | head -4
