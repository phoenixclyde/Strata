#!/bin/bash
set -u
S=~/strata166/work/r66
echo "########## A. --kv 的参数解析（所有取值） ##########"
grep -rn '"k8v4"\|"k8v8"\|"q4_0"\|kv_int8\|kv_q4' --include=*.cpp ~/strata166/pr/strata-fork/src/program/*.cpp 2>/dev/null | head -12

echo
echo "########## B. W4A4 / W4A8 两个实现并存？ ##########"
ls -l $S/src/prefill/mmq_nvfp4_w4a4.cu $S/src/prefill/mmq_nvfp4_w4a8.cu 2>/dev/null
echo "--- 各自头部注释 ---"
head -22 $S/src/prefill/mmq_nvfp4_w4a4.cu 2>/dev/null
echo "  ......"
head -22 $S/src/prefill/mmq_nvfp4_w4a8.cu 2>/dev/null

echo
echo "########## C. 这两个实例用什么指令 ##########"
for f in $S/src/prefill/mmq_nvfp4_w4a4.cu $S/src/prefill/mmq_nvfp4_w4a8.cu; do
  echo "--- $(basename $f) ---"
  grep -cE "v_dot8|sdot8|dot8_i32_i4" $f 2>/dev/null | sed 's/^/  dot8 命中: /'
  grep -nE "fp4|e2m1|E2M1|lut|table|__builtin_amdgcn" $f 2>/dev/null | head -6
done

echo
echo "########## D. 是否都编进二进制（CMake） ##########"
grep -n "nvfp4_w4a4\|nvfp4_w4a8" ~/strata166/pr/strata-fork/CMakeLists.txt 2>/dev/null | head -6
