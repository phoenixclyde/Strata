#!/bin/bash
O=/opt/rocm/llvm/bin/llvm-objdump
F=/out/gen15/1_BenchmarkProblems/Cijk_Ailk_Bjlk_HHS_BH_UserArgs_00/00_Final/caches/d95bdc892bfc/source/library/gfx906/Kernels.so-000-gfx906-xnack-.hsaco
echo "=== header ==="
$O -f "$F" 2>/dev/null | grep -iE 'format|architecture|triple' | head -4
echo "=== instruction census ==="
$O -d "$F" 2>/dev/null | grep -oE 'v_dot2_f32_f16|v_fma_mix_f32|v_mad_mix_f32|v_pk_fma_f16|v_pk_add_f16|v_mfma[a-z0-9_]*' | sort | uniq -c
echo "=== sample mac instrs ==="
$O -d "$F" 2>/dev/null | grep -E 'dot2|fma_mix|pk_fma' | head -6
echo "=== total instrs ==="
$O -d "$F" 2>/dev/null | grep -cE '^\s+[0-9a-f]+:'
