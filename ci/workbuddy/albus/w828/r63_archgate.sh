cd /home/albus/strata166/src028
for k in STRATA_Q8_PACKED STRATA_Q6_PACKED STRATA_MMVF_ROWS STRATA_ATTN_LANECELL STRATA_EXPERT_V2 STRATA_LFUSE STRATA_GDN_SPLIT STRATA_QFUSE STRATA_PLE_BATCH STRATA_HCD_EXACT STRATA_CVEC_FUSE STRATA_GDN_CONVL2 STRATA_GDN_NOY STRATA_HC_UPMIX; do
  echo "########## $k"
  grep -rn "getenv(\"$k\")" src include 2>/dev/null | head -3
  grep -rn "$k" src include 2>/dev/null | grep -iE "gfx1[0-9]|wave32|wave64|STRATA_USE_HIP|#if" | head -4
done
