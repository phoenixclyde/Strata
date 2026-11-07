#!/bin/bash
set -u
echo "=== 1. 我们的 Q4_K vec_dot 实现（完整读）==="
if [ -f ~/strata166/work/r60-gc/vecdotq.cuh ]; then
  F=~/strata166/work/r60-gc/vecdotq.cuh
else
  F=$(find ~/strata166 -name vecdotq.cuh 2>/dev/null | head -1)
fi
echo "file: $F"
grep -n "vec_dot_q4_K_q8_1" $F | head -3
sed -n "/static __device__ __forceinline__ int vec_dot_q4_K_q8_1/,/^}/p" $F | head -60

echo
echo "=== 2. MMQ 的对象文件（Q4_K 实例）==="
B=~/strata166/gfx029-build
find $B -name "*mmq*" -name "*.o" 2>/dev/null | head -10
echo "--- 静态库 ---"
ls -l $B/libstrata_mmq.a 2>/dev/null
ar t $B/libstrata_mmq.a 2>/dev/null | grep -iE "q4_k|q4k" | head -5
