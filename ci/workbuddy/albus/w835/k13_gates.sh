#!/bin/bash
# W835c: for each recent opt-in switch, is the gfx906 gap HARDWARE or just "not written"?
S=/home/albus/strata166/src028
cd $S || exit 1
for v in STRATA_CKPT_ASYNC STRATA_PARK_ASYNC STRATA_GRAPH_PRIO STRATA_CKPT_POOL \
         STRATA_EMBED_VRAM STRATA_DEQUANT_SIDE STRATA_DEQUANT_WIDE STRATA_PLE_COMPACT \
         STRATA_GDN_CHUNKED STRATA_HC_UPMIX STRATA_PF_FUSED_F16 STRATA_PF_FUSED_NT \
         STRATA_MMVQ_IL_PF STRATA_GDN_TC; do
  echo "######## $v"
  hit=$(grep -rn "$v" src include 2>/dev/null | head -3)
  if [ -z "$hit" ]; then echo "   (not in this tree)"; else echo "$hit" | sed 's/^/   /' | cut -c1-190; fi
  # the guard line just above the first use
  f=$(grep -rl "$v" src include 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    n=$(grep -n "$v" "$f" | head -1 | cut -d: -f1)
    s=$((n>18 ? n-18 : 1))
    echo "   --- guard context in ${f#src/} (line $s-$n) ---"
    sed -n "${s},${n}p" "$f" | grep -nE "__HIPCC__|__CUDA_ARCH__|gfx_arch_is|HIP_PLATFORM|defined\(__|#if|#else|#endif" | tail -6 | cut -c1-170 | sed 's/^/     /'
  fi
  echo
done
