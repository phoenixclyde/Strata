#!/bin/bash
set -u
P=~/strata166/pr/strata-fork
echo "########## A. prefill timing 的打印条件 ##########"
grep -rn "prefill timing" --include=*.cpp --include=*.cu --include=*.hpp $P/src 2>/dev/null | head -5

echo
echo "########## B. 上下文（是否被 env 控制 / 限流） ##########"
f=$(grep -rln "prefill timing" --include=*.cpp $P/src 2>/dev/null | head -1)
echo "file: $f"
L=$(grep -n "prefill timing" $f 2>/dev/null | head -1 | cut -d: -f1)
echo "line: $L"
[ -n "${L:-}" ] && sed -n "$((L-18)),$((L+3))p" $f

echo
echo "########## C. 日志里 81392 行之后是否有 prefill 相关 ##########"
docker exec strata166-407 sh -c "awk 'NR>81392 && /prefill/' /data/strata-huihui-ud-iq4_xs.log | tail -5" 2>&1 | cut -c1-150
echo "--- 81392 之后 prompt 行数 ---"
docker exec strata166-407 sh -c "awk 'NR>81392 && /strata serve: prompt/' /data/strata-huihui-ud-iq4_xs.log | wc -l" 2>&1
