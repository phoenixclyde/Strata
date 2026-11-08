#!/bin/bash
# W1058: preprocessor pickup test for the P3 variant (does -DSTRATA_MMQ_W4A4 reach the TU,
# and is the patched overlay vecdotq.cuh the one being included?)
set -u
R=/home/albus/strata166/pr/k10
OUT=/home/albus/strata166/build-masterp
W=/home/albus/strata166/tmp/w1058
IMG=strata-gfx906:0.2.11-101
docker run --rm -v "$R":/src -v "$OUT":/out -v /home/albus/strata166/tmp/w1037/llama-master:/llama.cpp -v "$W":/w -w /out "$IMG" bash -lc '
set -u
cd /out
CMD=$(head -1 /w/cmd_new.txt)
echo "W4A4_in_cmd=$(echo "$CMD" | grep -c STRATA_MMQ_W4A4)"
eval "$CMD -E -o /w/pp.ii"
echo PP_RC=$?
echo "marker_sdot8_comment=$(grep -c "sdot8 recenter" /w/pp.ii)"
echo "builtin_sdot8=$(grep -c "__builtin_amdgcn_sdot8" /w/pp.ii)"
echo "guard_name=$(grep -c "STRATA_MMQ_W4A4" /w/pp.ii)"
grep -n "vec_dot_q4_K_q8_1_impl_mmq" /w/pp.ii | head -3
# which vecdotq.cuh got included?
grep -n "vecdotq.cuh" /w/cmd.txt | head -2
'
