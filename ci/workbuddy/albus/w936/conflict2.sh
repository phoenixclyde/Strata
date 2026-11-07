#!/bin/bash
set -u
W=~/strata166/work/r77
cd "$W" || exit 1
echo "=== prepare_gated_window 结束后紧跟什么（找第一个 '\$' 或顶格函数） ==="
awk 'NR>=2874 && NR<=3000 && /^}/ {print NR": "$0; found=NR} found && NR>found && NR<=found+8 {print NR": "$0}' src/program/generate.cpp | head -20
echo
echo "=== 直接看 2950-3010 ==="
sed -n '2950,3010p' src/program/generate.cpp
echo
echo "=== main( 的位置 ==="
grep -n "^int main(\|^static int main(" src/program/generate.cpp | head -3
