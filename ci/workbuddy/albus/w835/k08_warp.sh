#!/bin/bash
# W835: is the whole codebase written for 32-lane warps on a 64-lane wave machine?
S=/home/albus/strata166/src028/src/kernels/cuda
cd $S
echo "=== A. 32-lane assumptions per file ==="
printf "%-26s %6s %6s %6s %6s\n" FILE "tid&31" "/32" ">>5" "warpSz"
for f in *.cu; do
  a=$(grep -c "& *31\|&31" $f 2>/dev/null)
  b=$(grep -c "/ *32\b" $f 2>/dev/null)
  c=$(grep -c ">> *5\b" $f 2>/dev/null)
  d=$(grep -c "warpSize" $f 2>/dev/null)
  tot=$((a+b+c))
  if [ "$tot" -gt 0 ] || [ "$d" -gt 0 ]; then
    printf "%-26s %6s %6s %6s %6s\n" "$f" "$a" "$b" "$c" "$d"
  fi
done | sort -k5 -rn | head -22
echo
echo "=== B. totals ==="
echo -n "  files mentioning warpSize: "; grep -rl "warpSize" *.cu *.cuh 2>/dev/null | wc -l
echo -n "  total '& 31'        : "; grep -rho "& *31" *.cu *.cuh 2>/dev/null | wc -l
echo -n "  total '>> 5'        : "; grep -rho ">> *5\b" *.cu *.cuh 2>/dev/null | wc -l
echo -n "  total '/ 32'        : "; grep -rho "/ *32\b" *.cu *.cuh 2>/dev/null | wc -l
echo -n "  literal 64 in blocks: "; grep -rho "dim3([0-9, ]*)" *.cu 2>/dev/null | sort | uniq -c | sort -rn | head -8
echo
echo "=== C. does Strata know about wave size at all? ==="
grep -rn "warpSize\|wavefront\|wave64\|64-lane" *.cu *.cuh 2>/dev/null | head -12
echo
echo "=== D. launch geometry distribution ==="
grep -rho "<<<[^>]*>>>" *.cu 2>/dev/null | head -0
grep -rn "dim3(" *.cu 2>/dev/null | head -14
