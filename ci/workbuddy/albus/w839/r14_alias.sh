#!/bin/bash
# W839-14 是否存在 STRATA_USE_HIP 的别名定义 + 读调用块结构
S=/home/albus/strata166/src028
echo "=== 谁 define 了 STRATA_USE_HIP ==="
grep -rIn 'define[[:space:]]*STRATA_USE_HIP' $S/src $S/include $S/CMakeLists.txt 2>/dev/null | head -10
echo "--- CMake 里 STRATA_USE_HIP 的出现 ---"
grep -n 'STRATA_USE_HIP' $S/CMakeLists.txt | head -10
echo
echo "=== generate.cpp 3330-3362 原文 ==="
awk 'NR>=3330 && NR<=3362 {printf "%5d| %s\n", NR, $0}' $S/src/program/generate.cpp
echo
echo "=== gfx906 那个块（#if defined(STRATA_HIP_GFX906)）起点与内容 ==="
N=$(grep -n 'defined(STRATA_HIP_GFX906)' $S/src/program/generate.cpp | head -1 | cut -d: -f1)
echo "first at $N"
awk -v n="$N" 'NR>=n && NR<=n+26 {printf "%5d| %s\n", NR, $0}' $S/src/program/generate.cpp
