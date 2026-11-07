#!/bin/bash
set -u
S=~/strata166/work/r66
P=~/strata166/pr/strata-fork
echo "########## A. 激活量化调用点：全局还是按类型？ ##########"
grep -rn "quantize_mmq_q8_1\|quantize_row_q8_1" --include=*.cu --include=*.cuh $S/src/prefill 2>/dev/null | grep -v "^.*://" | head -12

echo
echo "########## B. vec_dot_q4_K_q8_1 的签名（激活类型写死在名字里？） ##########"
grep -n "vec_dot_q4_K_q8_1\|vec_dot_type\|VDR_Q4_K" $S/src/prefill/vecdotq.cuh 2>/dev/null | head -10

echo
echo "########## C. MMQ 的类型分派表：一个类型一个实例还是可以叠加？ ##########"
grep -n "DECL_MMQ_CASE\|_strata_mmq_tab_types" $P/CMakeLists.txt 2>/dev/null | head -8
echo "--- tab types 清单 ---"
grep -n "set(_strata_mmq_tab_types" -A 6 $P/CMakeLists.txt 2>/dev/null

echo
echo "########## D. --kv int8 (=k8v8) 的显存与说明 ##########"
grep -rn "INT8 K + INT8\|int8 K\|k8v8\|816 B/cell\|bytes per cell" --include=*.hpp --include=*.cpp --include=*.cuh $P/include/strata $P/src/core 2>/dev/null | head -8
echo "--- kv 模式注释原文 ---"
sed -n '85,105p' $P/src/kernels/cuda/qsa_prompt_attn.cu 2>/dev/null

echo
echo "########## E. 生产 config 里 kv 的取值 ##########"
docker exec strata166-407 sh -c "grep -o '\"--kv\", *\"[a-z0-9_]*\"' /data/strata-huihui-ud-iq4_xs.json; grep -o '\"--kv [a-z0-9_]*\"' /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/cmdline 2>/dev/null" 2>/dev/null
docker exec strata166-407 sh -c "tr '\0' ' ' < /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/cmdline | grep -o '\-\-kv [a-z0-9_]*'" 2>/dev/null
