#!/bin/bash
T=/home/albus/strata166/gfx029
F=$T/src/kernels/fused_gr_bench.cpp
echo "=== include ==="
grep -n '#include' $F | head -12
echo "=== CMake 里的 target ==="
grep -rn "fused_gr_bench" $T/CMakeLists.txt | head -6
echo "=== 前 20 行注释（用法）==="
sed -n '1,16p' $F
