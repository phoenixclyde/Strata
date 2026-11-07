#!/bin/bash
# W835c: does dequant_wide even apply to us? and are the 4 bitwise decode switches gated on gfx906?
S=/home/albus/strata166/src028
cd $S || exit 1
echo "=== A. dequant_wide_on() call sites (which path uses it) ==="
grep -rn "dequant_wide_on\|g_dequant_wide\|wide_type" src include 2>/dev/null | grep -v "^src/kernels/cuda/dequant_bf16.cu:2[89]" | head -14
echo
echo "=== B. is that path taken when MMQ_KQ=1 ? ==="
grep -rn "mmq_plan\|native_mmq\|prefill_mmq" src/prefill/prefill.cpp src/prefill/gemm.cu 2>/dev/null | head -10
echo
echo "=== C. the 4 bitwise decode switches: any arch gate? ==="
for v in STRATA_ATTN_LANECELL STRATA_ATTN_MERGE_V2 STRATA_EXPDEC STRATA_TSUM; do
  echo "--- $v"
  grep -rn "$v" src include 2>/dev/null | head -2 | cut -c1-170
  f=$(grep -rl "$v" src include 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    n=$(grep -n "$v" "$f" | head -1 | cut -d: -f1); s=$((n>14?n-14:1))
    sed -n "${s},${n}p" "$f" | grep -nE "gfx_arch_is|__HIPCC__|#if|#elif" | tail -3 | cut -c1-160 | sed 's/^/     /'
  fi
done
echo
echo "=== D. GRAPH_PRIO: the full HIP guard ==="
sed -n '210,232p' src/core/verify.cpp | cut -c1-180
