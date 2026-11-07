#!/bin/bash
D=/home/albus/strata166/data
echo "=== [1] 所有 TTFT 拟合行（原始件） ==="
grep -a -rn "linear fit" $D/*.log $D/*.txt /home/albus/strata166/tmp/*.log 2>/dev/null | sed 's#/home/albus/strata166/##' | head -20
echo
echo "=== [2] TTFT 逐点（raw lines with s and likely tok） ==="
for tag in tp tq ts; do
  echo "--- $tag ---"
  grep -a -h -E "^\s*(warm|[0-9]+ tok|tok=|prompt|TTFT)" $D/w828_${tag}*.log 2>/dev/null | head -14
done
echo
echo "=== [3] W830 A/B 的 fit 行 ==="
grep -a -E "fit:|ARM|MEDIAN" $D/w830_ab.log 2>/dev/null | head -24
echo
echo "=== [4] W828 §6.1 的 decode 样本（0.1.53 vs 0.1.54n） ==="
grep -a -rn "45.9\|45.74\|45\.7" $D/w828*.log 2>/dev/null | head -10
echo
echo "=== [5] 有哪些 w828/w830 原始日志 ==="
ls -la $D/w828*.log $D/w830*.log 2>/dev/null | head -20
