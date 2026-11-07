#!/bin/bash
set -u
cd ~/strata166/pr/strata-fork || exit 1

echo "=== 1. prefill 的阶段计时点（trace 输出）==="
grep -n "strata trace: prompt chunk" src/prefill/prefill.cpp | head -5
sed -n '3100,3120p' src/prefill/prefill.cpp

echo
echo "=== 2. attention 在 prefill 里的位置（qsa_prompt_attn 调用点）==="
grep -rn "qsa_prompt_attn\|attn_prompt\|prompt_attn" --include=*.cpp --include=*.cu src/prefill/ src/kernels/cuda/ 2>/dev/null | grep -vE "^.*://" | head -10

echo
echo "=== 3. 日志里已有的 attention 占比证据 ==="
docker exec strata166-407 sh -c "grep -inE 'attn|attention' /data/strata-huihui-ud-iq4_xs.log | grep -iE '%|ms|share' | tail -8 | cut -c1-170"
