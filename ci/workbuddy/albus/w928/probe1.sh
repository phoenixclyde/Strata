#!/bin/bash
# W928: 查 MMQ 激活格式 + KV cache 格式 + 是否支持混合精度
set -u
SRC=~/strata166/pr/strata-fork
echo "########## 1. --kv 的取值与实现 ##########"
grep -rn "k8v4\|k8v8\|k8v\b\|kv_mode\|KV_MODE" --include=*.cpp --include=*.hpp --include=*.cu --include=*.h "$SRC/src" "$SRC/include" 2>/dev/null | grep -vE "test|\.md" | head -20

echo
echo "########## 2. KV_MODE 的分派（launch<3> 那些） ##########"
grep -rn "KV_MODE" --include=*.cu --include=*.cuh "$SRC/src/kernels/cuda/qsa_prompt_attn.cu" 2>/dev/null | head -15

echo
echo "########## 3. MMQ 激活 Q8_1 的来源 ##########"
grep -rn "Q8_1\|q8_1\|quantize_mmq_q8_1\|to_q8_1" --include=*.cu --include=*.cuh "$SRC/work" 2>/dev/null | head -5
grep -rln "quantize_mmq_q8_1\|mul_mat_q_case" ~/strata166/work/r66/src/prefill 2>/dev/null | head -5

echo
echo "########## 4. 是否有逐层/逐类型不同量化 ##########"
grep -rn "per.layer\|per_layer\|layer.*quant\|mixed.*precision" --include=*.hpp --include=*.cpp "$SRC/include/strata" 2>/dev/null | head -8

echo
echo "########## 5. mmq-config-gcn 里 Q4_K 那几行的 cc 参数含义 ##########"
grep -n "struct ggml_cuda_mmq_config" -A 18 "$SRC/third_party/ggml/src/ggml-cuda/common.cuh" 2>/dev/null | head -22
