#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
C="docker exec strata166-407"

echo "########## A. --prefill 的解析与 auto 的取值 ##########"
grep -rn '"auto"\|prefill.*chunk\|chunk.*auto' --include=*.cpp $S/src/program/generate.cpp 2>/dev/null | grep -i "chunk\|prefill" | head -10

echo
echo "########## B. chunk 大小的决策函数 ##########"
grep -rn "prompt chunk auto\|chunk auto:" --include=*.cpp --include=*.hpp $S/src 2>/dev/null | head -4

echo
echo "########## C. CPU share 阈值（1024） ##########"
grep -rn "CPU share is ON\|1024" --include=*.cpp $S/src/prefill/prefill.cpp 2>/dev/null | head -6

echo
echo "########## D. 日志：实际 chunk 数与大小 ##########"
$C sh -c "grep -inE 'prompt chunk|chunks of|chunk [0-9]+ of' /data/strata-huihui-ud-iq4_xs.log | tail -8" 2>&1 | cut -c1-180

echo
echo "########## E. 每次 prefill 的 chunk 数（从 timing 行推断） ##########"
$C sh -c "grep -c 'strata prefill timing: [0-9]' /data/strata-huihui-ud-iq4_xs.log" 2>&1
$C sh -c "grep 'strata prefill timing: [0-9]' /data/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-120" 2>&1
