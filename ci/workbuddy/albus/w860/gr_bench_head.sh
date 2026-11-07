#!/bin/bash
T=/home/albus/strata166/gfx029
F=$T/src/kernels/fused_gr_bench.cpp
echo "=== 行数 ==="; wc -l $F
echo "=== main / 参数 ==="
grep -n "int main\|argv\|T =\|N =\|LR\b\|HC\b\|iters\|printf" $F | head -24
