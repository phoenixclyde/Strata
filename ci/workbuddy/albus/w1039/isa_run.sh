#!/bin/bash
set -u
S=/home/albus/strata166
B=$S/build-pa3
IMG=strata-gfx906:0.2.11-101
docker run --rm -v "$S/pr/port-all":/src -v "$B":/out -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" \
  sh -c '
set -u
t=CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o
ninja -t commands "$t" 2>/dev/null | tail -1 > /tmp/cmd.txt
cmd=$(cat /tmp/cmd.txt)
# swap -c for -S
new=$(printf "%s" "$cmd" | sed "s| -c | -S -o /tmp/qda.s |")
printf "%s" "$new" > /tmp/cmd2.sh
bash /tmp/cmd2.sh 2>/tmp/err.txt; echo RC=$?
tail -3 /tmp/err.txt
ls -l /tmp/qda.s 2>/dev/null
if [ -f /tmp/qda.s ]; then
  for p in v_dot4_i32_i8 v_fma_f32 v_cvt_f32_i32 v_mul_f32 v_max_f32 v_rcp_iflag_f32 v_lshrrev_b32 v_cndmask_b32; do
    printf "%-20s %s\n" "$p" "$(grep -c "$p" /tmp/qda.s)"
  done
  echo "---- kernels (first 12) ----"
  grep -c "^_Z" /tmp/qda.s || true
fi
'
