#!/bin/bash
# W837: how the arch predicates and defaults are structured, so we add gfx906 the same way
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== A. gfx_arch.hpp (the predicate header) ==="
sed -n '1,80p' include/strata/kernels/gfx_arch.hpp | cut -c1-190
echo
echo "=== B. arch_defaults.hpp (the interface) ==="
cat include/strata/core/arch_defaults.hpp 2>/dev/null | cut -c1-190
echo
echo "=== C. where apply_arch_defaults is called ==="
grep -rn "apply_arch_defaults\|arch_default_env" src --include=*.cpp | grep -v arch_defaults.cpp | head -8
