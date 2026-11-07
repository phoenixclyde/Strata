#!/bin/bash
S=/home/albus/strata166/pr/k10
echo "=== A. help 文本里各 kv 模式 ==="
sed -n 1045,1070p $S/src/program/generate.cpp
echo "=== B. cell 字节数定义 ==="
grep -rn "816\|bytes_per_cell\|cell_bytes\|kv_cell" $S/src/core/*.cpp $S/src/core/*.hpp $S/src/kernels/*.cpp 2>/dev/null | head -25
echo "=== C. qsa_set_kv_hybrid / kv_int8 / kv_q4 ==="
grep -rn "void qsa_set_kv_\|qsa_set_kv_hybrid\|qsa_set_kv_int8\|qsa_set_kv_q4" $S/src --include=*.cpp --include=*.hpp | head -20
echo "=== D. 生产日志里的 kv 行 ==="
grep -iE "kv (int8|hybrid|k8v4|q4)|kv-int8|kv_hybrid|816 B" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -8
