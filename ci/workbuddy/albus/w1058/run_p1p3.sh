#!/bin/bash
# W1058: build + run the R91 P1+P3 harness + microbench in a scratch container. Zero production impact.
# Compile flags copied VERBATIM from build-masterp build.ninja mmq-instance-q4_k rule
#   FLAGS = -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906
#   DEFINES = -DGGML_USE_HIP -DSTRATA_HIP_GFX906=1 -DSTRATA_MMQ_KQUANTS=1 -DSTRATA_MMQ_TQ=1 \
#             -DSTRATA_MMQ_TQP=1 -DSTRATA_Q6K_EXPERTS=1 -DSTRATA_VERIFY_MAX_T=8 \
#             -DSTRATA_VERSION=\"0.1.57\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1
W=/home/albus/strata166/tmp/w1058
IMG=strata-gfx906:0.2.11-101
mkdir -p $W
docker run --rm --device=/dev/kfd --device=/dev/dri -v $W:/w $IMG bash -lc '
hipcc -x hip -O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 \
  -DGGML_USE_HIP -DSTRATA_HIP_GFX906=1 -DSTRATA_MMQ_KQUANTS=1 -DSTRATA_MMQ_TQ=1 \
  -DSTRATA_MMQ_TQP=1 -DSTRATA_Q6K_EXPERTS=1 -DSTRATA_VERIFY_MAX_T=8 \
  -DSTRATA_VERSION=\"0.1.57\" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1 \
  /w/r91_p1p3.cu -o /w/r91_p1p3 2>/w/build.err
rc=$?
echo BUILD_RC=$rc
if [ $rc != 0 ]; then grep -E "error:" /w/build.err | head -40; exit 1; fi
echo ==== ISA smoke: does the fatbin contain v_dot8_i32_i4 ?
(llvm-objdump -d /w/r91_p1p3 2>/dev/null | grep -c "v_dot8_i32_i4" | head -1) || true
for i in 1 2 3; do
  echo "=== RUN $i reps=8 trials=5 ==="
  timeout 600 /w/r91_p1p3 8 5
done
'
