#!/bin/bash
# W835c: census of architecture-conditional code in Strata -- what gfx906 lacks a path for
S=/home/albus/strata166/src028
cd $S || exit 1
echo "=== A. arch predicates available ==="
grep -rhoE "gfx_arch_is_[a-z0-9_]+\(" src include 2>/dev/null | sort | uniq -c | sort -rn | head -20
echo
echo "=== B. files that branch on arch, with which arch ==="
for f in $(grep -rl "gfx_arch_is_\|__CUDA_ARCH__\|HIP_PLATFORM_AMD\|__HIPCC__" src include 2>/dev/null | head -60); do
  g9=$(grep -c "gfx906" $f 2>/dev/null)
  g11=$(grep -c "gfx11" $f 2>/dev/null)
  g12=$(grep -c "gfx12" $f 2>/dev/null)
  cu=$(grep -c "__CUDA_ARCH__" $f 2>/dev/null)
  tot=$((g9+g11+g12))
  if [ "$tot" -gt 0 ] || [ "$cu" -gt 0 ]; then
    printf "  %-46s gfx906=%-3s gfx11x=%-3s gfx12=%-3s CUDA_ARCH=%-3s\n" "${f#src/}" "$g9" "$g11" "$g12" "$cu"
  fi
done | sort -t= -k2 -rn | head -40
echo
echo "=== C. arch_defaults.cpp : which arch tables exist ==="
AD=$(find src include -name "arch_defaults*" 2>/dev/null | head -1); echo "file=$AD"
grep -nE "gfx[0-9]{3,4}|sm_[0-9]+|arch|struct|static const|constexpr" "$AD" 2>/dev/null | head -40
