#!/bin/bash
# W839-27 谓词与前缀匹配
S=/home/albus/strata166/src028
echo "=== gfx_arch_is_gfx906 实现 ==="
grep -rn -A12 'bool gfx_arch_is_gfx906' $S/src/kernels/gfx_arch.cpp 2>/dev/null | head -20
grep -rn -A12 'gfx_arch_is_gfx906' $S/include/strata/kernels/gfx_arch.hpp | head -24
echo
echo "=== gfx906_tuned_env 实现 ==="
N=$(grep -n 'gfx906_tuned_env' $S/src/core/arch_defaults.cpp | head -1 | cut -d: -f1)
awk -v n="$N" 'NR>=n-6 && NR<=n+34 {printf "%5d| %s\n", NR, $0}' $S/src/core/arch_defaults.cpp
echo
echo "=== arch_default_env 里 gfx906 的分支 ==="
grep -n -B2 -A10 'gfx_arch_is_gfx906' $S/src/core/arch_defaults.cpp | head -40
