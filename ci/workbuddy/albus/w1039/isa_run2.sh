#!/bin/bash
set -u
S=/home/albus/strata166
IMG=strata-gfx906:0.2.11-101
docker run --rm -v "$S/tmp/w1040":/w -v "$S/pr/port-all":/src -v "$S/build-pa3":/out \
  -v "$S/tmp/w1037/llama-master":/llama.cpp -w /out "$IMG" sh -c '
set -u
t=CMakeFiles/strata_kernels.dir/src/kernels/cuda/qsa_decode_attn.cu.o
cmd=$(ninja -t commands "$t" 2>/dev/null | tail -1)
new=$(printf "%s" "$cmd" | sed "s| -c | -S -o /w/qda.s |")
printf "%s" "$new" > /w/cmd2.sh
bash /w/cmd2.sh 2>/w/err.txt; echo RC=$?
ls -l /w/qda.s
echo "---- head ----"
sed -n 1,12p /w/qda.s
echo "---- mnemonic sample ----"
grep -m5 -E "^\s+v_" /w/qda.s
echo "---- counts ----"
for p in v_dot4 v_fma_f32 v_cvt_f32_i32 v_mul_f32 v_max_f32 v_rcp s_endpgm ds_bpermute; do
  printf "%-18s %s\n" "$p" "$(grep -c "$p" /w/qda.s)"
done
echo "---- how many lines ----"
wc -l /w/qda.s
'
