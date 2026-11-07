#!/bin/sh
cd /tmp
/opt/rocm/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 \
  -I/repo/include -I/repo/include/strata/hip_compat -I/repo/src -DSTRATA_HIP_GFX906 \
  -S /repo/src/kernels/cuda/qsa_decode_attn.cu -o q.s 2>&1 | head -5
echo "dot4=$(grep -c v_dot4_i32_i8 q.s) dpp=$(grep -c _dpp q.s) bpermute=$(grep -c ds_bpermute q.s)"
/opt/rocm/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 \
  -I/repo/include -I/repo/include/strata/hip_compat -I/repo/src -DSTRATA_HIP_GFX906 \
  -S /repo/src/kernels/cuda/native_router.cu -o r.s 2>&1 | head -5
echo "router: dpp=$(grep -c _dpp r.s) bpermute=$(grep -c ds_bpermute r.s)"
