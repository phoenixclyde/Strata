#!/bin/bash
# W837: what does each of our 14 switches default to, and does it change bits?
W=/home/albus/strata166/gfx906
cd $W || exit 1
for v in STRATA_GFX906_ATTN_QUERY_SWIZZLE STRATA_GFX906_ATTN_REDUCE12 STRATA_GDN_HEAD STRATA_GDN_PP \
         STRATA_HC_Q8 STRATA_SELECT_SIMT STRATA_ROUTE_TAIL_SKIP STRATA_MMQ_KQ STRATA_HIP_PROMPT_F16 \
         STRATA_PREFILL_CPU_SHARE STRATA_RESIDENT_HEADROOM_GIB STRATA_ATTN_DAILY; do
  echo "######## $v"
  grep -rn "$v" src include --include=*.cpp --include=*.cu --include=*.hpp --include=*.cuh 2>/dev/null \
    | grep -vE "arch_defaults|_test" | head -2 | cut -c1-175 | sed 's/^/   /'
  # the default when unset
  f=$(grep -rl "$v" src --include=*.cpp --include=*.cu 2>/dev/null | grep -vE "arch_defaults|_test" | head -1)
  if [ -n "$f" ]; then
    n=$(grep -n "$v" "$f" | head -1 | cut -d: -f1)
    s=$((n>4?n-4:1))
    sed -n "${s},$((n+3))p" "$f" | grep -E "getenv|return|default|= *[01]|nullptr" | head -4 | cut -c1-170 | sed 's/^/     /'
  fi
  echo
done
