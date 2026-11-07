#!/bin/bash
set -u
S=~/strata166/pr/strata-fork

echo "########## A. chunk 的切分循环 ##########"
grep -n "prefill_chunk\|chunk_tokens\|for (int64_t off" $S/src/prefill/prefill.cpp 2>/dev/null | head -18

echo
echo "########## B. auto 的决策（generate.cpp 9600-9680） ##########"
sed -n '9640,9675p' $S/src/program/generate.cpp

echo
echo "########## C. chunk 循环体（找 n > chunk 的分支） ##########"
grep -n "std::min(.*chunk\|chunk = std::min\|<= chunk\|> chunk" $S/src/prefill/prefill.cpp 2>/dev/null | head -12

echo
echo "########## D. kStreamAllMin 与 CPU share 的判定 ##########"
sed -n '214,240p' $S/src/prefill/prefill.cpp
