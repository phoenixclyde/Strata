#!/bin/bash
set -u
W=~/strata166/work/r66
cd $W || exit 1

echo "=== STRATA_USE_HIP 在哪里定义 ==="
grep -rn "define STRATA_USE_HIP" include/ src/ 2>/dev/null | head -5
grep -rn "STRATA_USE_HIP" CMakeLists.txt cmake/*.cmake 2>/dev/null | head -5

echo
echo "=== 补丁里 #if 包裹的范围 ==="
grep -n "STRATA_USE_HIP" src/program/generate.cpp | head -6

echo
echo "=== generate.cpp 是否间接包含 hip 头 ==="
grep -n "strata_hip.h\|hip_compat" include/strata/platform/hip_compat/strata_hip.h 2>/dev/null | head -2
sed -n '1,40p' include/strata/platform/hip_compat/strata_hip.h | grep -nE "define STRATA_USE_HIP|if defined|pragma once" | head -5

echo
echo "=== 用编译命令里的 -D 做预处理测试 ==="
/opt/rocm/llvm/bin/clang++ -DSTRATA_HIP_GFX906=1 -D__HIP_PLATFORM_AMD__=1 -I$W/include -isystem $W/include/strata/platform/hip_compat -isystem /opt/rocm/include -E -dM -x c++ /dev/null 2>/dev/null | grep -c STRATA_USE_HIP || true
