#!/bin/bash
# W836: add the missed W794 file, verify all five, then commit as separate units
F=/home/albus/strata166/pr/strata-fork
S=/home/albus/strata166/src028
cd $F || exit 1

echo "=== A. the file I missed: qsa_decode_attn.cu (W794) ==="
cp -a "$S/src/kernels/cuda/qsa_decode_attn.cu" "$F/src/kernels/cuda/qsa_decode_attn.cu"
n=$(git diff -U0 -- src/kernels/cuda/qsa_decode_attn.cu | grep -cE '^[+-][^+-]')
echo "  changed lines now: $n"
echo
echo "=== B. full change set ==="
git diff --stat
echo
echo "=== C. W794 content (should be the swizzle + reduce12 markers) ==="
git diff -U1 -- src/kernels/cuda/qsa_decode_attn.cu | grep -E '^[+-][^+-]' | head -20
echo
echo "=== D. config identity ==="
git config user.name 2>/dev/null || echo "(no user.name)"
git config user.email 2>/dev/null || echo "(no user.email)"
