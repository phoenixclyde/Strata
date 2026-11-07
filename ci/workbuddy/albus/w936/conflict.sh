#!/bin/bash
set -u
W=~/strata166/work/r77
cd "$W" || exit 1
echo "=== prepare_gated_window 结尾定位 ==="
grep -n "prepare_gated_window" src/program/generate.cpp | head -5
echo "--- 该函数结尾附近 ---"
L=$(grep -n "static bool prepare_gated_window" src/program/generate.cpp | head -1 | cut -d: -f1)
[ -n "$L" ] && sed -n "$((L-2)),$((L+2))p" src/program/generate.cpp
echo
echo "=== 找 return true; } 后紧跟 engine_main 的那处 ==="
grep -n "static int engine_main" src/program/generate.cpp | head -3
L2=$(grep -n "static int engine_main" src/program/generate.cpp | head -1 | cut -d: -f1)
echo "engine_main 在 $L2"
[ -n "$L2" ] && sed -n "$((L2-12)),$((L2+2))p" src/program/generate.cpp
