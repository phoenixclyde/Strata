#!/bin/bash
# W1058/R91-P3: A/B ISA assertion on the REAL Q4_K mmq instance (corrected target).
#
# TRAP (W1058 实测): mmq-instance-q4_k.cu includes "../mmq.cuh" (RELATIVE), which resolves
# to the llama-master tree copy (/llama.cpp/ggml/src/ggml-cuda/*), NOT the build overlay
# (/out/ggml-tq-overlay/*) — the overlay -I only wins for directly-compiled TUs like
# quantize.cu (which is why W1057's a4sim worked). Patching overlay headers is a no-op
# for the mmq-instance TUs.  Effective target = llama-master tree copy.
#
#   baseline = existing mmq-instance-q4_k.cu.o (clean tree, DOT4=5184/DOT8=0 from W1058 run1)
#   candidate = same TU recompiled with -DSTRATA_MMQ_W4A4=1 + patched vecdotq.cuh
# Compile command copied VERBATIM from `ninja -t commands` (+ the one define). Restored after.
set -u
OUT=/home/albus/strata166/build-masterp
L=/home/albus/strata166/tmp/w1037/llama-master
W=/home/albus/strata166/tmp/w1058
IMG=strata-gfx906:0.2.11-101
V=$L/ggml/src/ggml-cuda/vecdotq.cuh
VO=$OUT/ggml-tq-overlay/vecdotq.cuh
OBJ=CMakeFiles/strata_mmq.dir/llama.cpp/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu.o
LOG=$W/isa_ab.log
: > "$LOG"
cp -f "$V" "$W/vecdotq.cuh.orig"
cp -f "$VO" "$W/vecdotq.overlay.orig"
echo "orig md5 L=$(md5sum "$V" | cut -c1-8) overlay=$(md5sum "$VO" | cut -c1-8)" >>"$LOG"
python3 "$W/p3_vecdot_patch.py" "$V" >>"$LOG" 2>&1 || { echo PATCH_FAIL; cp -f "$W/vecdotq.cuh.orig" "$V"; exit 1; }
cp -f "$V" "$VO"   # keep the pair in sync
echo "patched md5 $(md5sum "$V" | cut -c1-8)" >>"$LOG"
docker run --rm -v /home/albus/strata166/pr/k10:/src -v "$OUT":/out -v "$L":/llama.cpp -v "$W":/w -w /out "$IMG" bash -lc '
set -u
cd /out
ninja -t commands '"$OBJ"' > /w/cmd.txt 2>/dev/null
CMD=$(head -1 /w/cmd.txt)
NEW=$(echo "$CMD" | sed "s#-o '"$OBJ"'#-o /w/q4k_w4a4.o#" | sed "s#-DGGML_USE_HIP#-DSTRATA_MMQ_W4A4=1 -DGGML_USE_HIP#")
echo "$NEW" > /w/cmd_new.txt
eval "$NEW" > /w/compile.log 2>&1
echo "COMPILE_RC=$?" >> /w/isa_ab.log
grep -m5 "error:" /w/compile.log >> /w/isa_ab.log
# include proof: the preprocessed TU must carry the variant marker
eval "$NEW -E -o /w/pp.ii" >/dev/null 2>&1
echo "pp_marker_sdot8_comment=$(grep -c "sdot8 recenter" /w/pp.ii)" >> /w/isa_ab.log
echo "pp_builtin_sdot8=$(grep -c "__builtin_amdgcn_sdot8" /w/pp.ii)" >> /w/isa_ab.log
for tag in base cand; do
  if [ $tag = base ]; then cp '"$OBJ"' /tmp/isa_$tag.o; else cp /w/q4k_w4a4.o /tmp/isa_$tag.o; fi
  cd /tmp
  llvm-objcopy --dump-section .hip_fatbin=fb_$tag.bin isa_$tag.o 2>/dev/null
  clang-offload-bundler --type=o --unbundle --targets=hip-amdgcn-amd-amdhsa--gfx906 --input=fb_$tag.bin --output=dev_$tag.o 2>/dev/null
  llvm-objdump -d dev_$tag.o > dev_$tag.dis 2>&1
  echo "$tag DOT4 $(grep -c v_dot4_i32_i8 dev_$tag.dis) DOT8 $(grep -c v_dot8_i32_i4 dev_$tag.dis)" >> /w/isa_ab.log
done
' >>"$LOG" 2>&1
RC=$?
cp -f "$W/vecdotq.cuh.orig" "$V"
cp -f "$W/vecdotq.overlay.orig" "$VO"
echo "restored L=$(md5sum "$V" | cut -c1-8) overlay=$(md5sum "$VO" | cut -c1-8)" >>"$LOG"
echo "DOCKER_RC=$RC" >>"$LOG"
cat "$LOG"
