#!/bin/bash
# W839-15 取插入锚点（3376-3430）
S=/home/albus/strata166/src028
awk 'NR>=3376 && NR<=3432 {printf "%5d| %s\n", NR, $0}' $S/src/program/generate.cpp
echo
echo "=== 上下文：W717 的历史注释（CMakeLists 698-710）==="
awk 'NR>=696 && NR<=712 {printf "%5d| %s\n", NR, $0}' $S/CMakeLists.txt
