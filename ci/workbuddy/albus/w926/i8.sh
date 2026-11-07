#!/bin/bash
set -u
cd ~/strata166/pr/strata-fork || exit 1

echo "=== 1. i8 kernel 的存在与签名 ==="
sed -n '536,560p' src/kernels/cuda/qsa_prompt_attn.cu

echo
echo "=== 2. i8 kernel 的调用点（谁选它）==="
grep -rn "prompt_attn_i8_kernel" --include=*.cu --include=*.cpp src/ | head -6

echo
echo "=== 3. qsa_prompt_attn_batch 里怎么选 ==="
grep -rn "qsa_prompt_attn_batch" --include=*.cu src/kernels/cuda/ | head -3
grep -n "i8\|I8\|int8" src/kernels/cuda/qsa_prompt_attn.cu | grep -iE "bool|if|env|requested|enable" | head -10

echo
echo "=== 4. 相关开关 ==="
grep -rn "STRATA_PROMPT_ATTN_I8\|PROMPT_ATTN_OLD\|prompt_attn_i8" --include=*.cu --include=*.cpp --include=*.hpp src/ include/ | head -8

echo
echo "=== 5. 生产日志里 attention 走哪条路 ==="
docker exec strata166-407 sh -c "grep -inE 'prompt_attn|qsa.*attn|attn.*i8|i8.*attn' /data/strata-huihui-ud-iq4_xs.log | tail -8 | cut -c1-165"
