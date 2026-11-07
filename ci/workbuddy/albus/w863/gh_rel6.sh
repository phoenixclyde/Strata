#!/bin/bash
R=/home/albus/strata166/pr/strata-fork
echo "=== apply_arch_defaults call sites in the WORKING TREE (HEAD 642de24f) ==="
grep -n "apply_arch_defaults" "$R/src/program/generate.cpp"
echo
echo "=== the guard above the first call ==="
n=$(grep -n "apply_arch_defaults" "$R/src/program/generate.cpp" | head -1 | cut -d: -f1)
sed -n "$((n-22)),$((n+6))p" "$R/src/program/generate.cpp"
echo
echo "=== is STRATA_USE_HIP defined in this build? ==="
grep -m1 "STRATA_USE_HIP" /home/albus/strata166/gfx029-build/build.ninja | cut -c1-160
echo -n "count of -DSTRATA_USE_HIP in build.ninja: "; grep -c -- "-DSTRATA_USE_HIP" /home/albus/strata166/gfx029-build/build.ninja
echo
echo "=== simt2 present in the working tree? ==="
grep -c "block_scores_simt2_kernel" "$R/src/kernels/cuda/qsa_select.cu"
echo "=== but the DEPLOYED binary prints which simt level? (from log) ==="
grep -a "qsa select" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2
echo "=== and the arch-defaults banner (proves apply_arch_defaults ran) ==="
grep -a "gfx906 (MI50-class)" /home/albus/strata166/data/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-130
