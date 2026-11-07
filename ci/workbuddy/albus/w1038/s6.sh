#!/bin/bash
S=/home/albus/strata166/pr/k10
echo "=== A. kv_q8.hpp 前 60 行 ==="
sed -n 1,60p $S/include/strata/kernels/kv_q8.hpp
echo
echo "=== B. kv_q4.hpp 前 60 行 ==="
sed -n 1,60p $S/include/strata/kernels/kv_q4.hpp 2>/dev/null
echo
echo "=== C. QsaShapes 结构 ==="
grep -rn -A14 "struct QsaShapes" $S/include/strata --include=*.hpp | head -30
