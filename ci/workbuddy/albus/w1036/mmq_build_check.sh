#!/bin/sh
G=/tmp/w1036/ggml-test
cd /tmp
for tag in base staged; do
  DEF=""
  [ "$tag" = "staged" ] && DEF="-DSTRATA_GFX906_MMQ_STAGE"
  /opt/rocm/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 $DEF \
    -I$G/include -I$G/src -I$G/src/ggml-cuda -DGGML_USE_HIP \
    -S $G/src/ggml-cuda/mmq.cu -o mmq_$tag.s 2>&1 | head -6
  if [ -f mmq_$tag.s ]; then
    echo "$tag: OK lines=$(wc -l < mmq_$tag.s) dot4=$(grep -c v_dot4_i32_i8 mmq_$tag.s) gld=$(grep -c global_load $mmq_$tag.s) ds_write=$(grep -c ds_write $mmq_$tag.s) waitcnt=$(grep -c s_waitcnt mmq_$tag.s)"
  else
    echo "$tag: FAILED"
  fi
done
