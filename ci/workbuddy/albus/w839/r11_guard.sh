#!/bin/bash
# W839-11 找 apply_arch_defaults 外层条件
S=/home/albus/strata166/src028
L=$(grep -n 'apply_arch_defaults' $S/src/program/generate.cpp | head -1 | cut -d: -f1)
echo "call at line $L"
echo "=== 往回找最近的 #if / if ( ==="
awk -v n="$L" 'NR>=n-120 && NR<=n {printf "%5d| %s\n", NR, $0}' $S/src/program/generate.cpp | grep -nE '#if|#endif|#else|if \(|else if' | tail -22
echo
echo "=== 该区间原文 3300-3380 的关键行 ==="
awk 'NR>=3300 && NR<=3380 {printf "%5d| %s\n", NR, $0}' $S/src/program/generate.cpp | grep -E '#if|#endif|if \(|all_igpu|ad\.' | head -24
