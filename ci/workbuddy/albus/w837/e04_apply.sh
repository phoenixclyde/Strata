#!/bin/bash
# W837: the apply_arch_defaults body, so the gfx906 table plugs in the same way
W=/home/albus/strata166/gfx906
cd $W || exit 1
echo "=== A. apply_arch_defaults (full) ==="
awk 'NR>=149 && NR<=200' src/core/arch_defaults.cpp | cut -c1-185
echo
echo "=== B. the exact spot where gfx906 would branch in ==="
grep -n "gfx_arch_is_gfx12\|gfx_arch_is_gfx1151\|return t;" src/core/arch_defaults.cpp | head -12
