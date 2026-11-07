#!/bin/bash
set -u
S=~/strata166/pr/strata-fork

echo "########## A. --prefill auto:N 的解析 ##########"
grep -n "auto:" $S/src/program/generate.cpp 2>/dev/null | head -10
echo "--- 上下文 ---"
L=$(grep -n '"auto:"' $S/src/program/generate.cpp 2>/dev/null | head -1 | cut -d: -f1)
[ -n "${L:-}" ] && sed -n "$((L-8)),$((L+14))p" $S/src/program/generate.cpp

echo
echo "########## B. 帮助文本里 auto 的完整说明 ##########"
sed -n '1094,1100p' $S/src/program/generate.cpp

echo
echo "########## C. auto 上限常量 ##########"
grep -n "kAutoChunkMax\|prefill_auto_max\|8192" $S/src/program/generate.cpp 2>/dev/null | grep -i "auto\|chunk" | head -8
