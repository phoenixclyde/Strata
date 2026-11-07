#!/bin/sh
# 同一份 iq_kernels.cu，分别在「A0 前（生产树）」与「A0 后（port-all）」下编成设备汇编，数指令。
cd /tmp
for tag in pre post; do
  case $tag in
    pre)  SRC=/src-pre ;;
    post) SRC=/src-post ;;
  esac
  /opt/rocm/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 \
    -I$SRC/include -I$SRC/include/strata/hip_compat -I$SRC/src -I/llama.cpp/ggml/include -I/llama.cpp/ggml/src -I/llama.cpp/ggml/src/ggml-cuda -DSTRATA_HIP_GFX906 \
    -S $SRC/src/kernels/cuda/iq_kernels.cu -o $tag.s 2>&1 | head -3
  echo "$tag: dot4=$(grep -c v_dot4_i32_i8 $tag.s) v_cmp_sdwa=$(grep -c v_cmp_lt_u32_sdwa $tag.s) cndmask=$(grep -c v_cndmask $tag.s) mul_i24=$(grep -c v_mul_i32_i24 $tag.s) mad_i24=$(grep -c v_mad_i32_i24 $tag.s) dot2_f32_f16=$(grep -c v_dot2_f32_f16 $tag.s)"
done
