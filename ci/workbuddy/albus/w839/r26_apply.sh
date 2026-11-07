#!/bin/bash
# W839-26 读 apply_arch_defaults 的实现与打印条件
S=/home/albus/strata166/src028
N=$(grep -n 'apply_arch_defaults' $S/src/core/arch_defaults.cpp | head -1 | cut -d: -f1)
echo "apply at $N"
awk -v n="$N" 'NR>=n && NR<=n+70 {printf "%5d| %s\n", NR, $0}' $S/src/core/arch_defaults.cpp
