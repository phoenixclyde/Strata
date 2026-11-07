#!/bin/bash
set -u
S=/home/albus/strata166
IMG=strata-gfx906:0.2.11-101
cat > "$S/tmp/w1041/t_fdot2.cu" <<'EOF'
#include <hip/hip_runtime.h>
#include <hip/hip_fp16.h>
__global__ void k(const __half2* a, const __half2* b, float* out) {
    float acc = 0.0f;
    #pragma unroll
    for (int j = 0; j < 4; ++j) acc = __builtin_amdgcn_fdot2(a[j], b[j], acc, false);
    out[threadIdx.x] = acc;
}
EOF
docker run --rm -v "$S/tmp/w1041":/w -w /w "$IMG" \
  /opt/rocm/lib/llvm/bin/clang++ -x hip --offload-arch=gfx906 --cuda-device-only -O3 -c t_fdot2.cu -o t_fdot2.o 2>&1 | head -20
echo "RC=$?"
docker run --rm -v "$S/tmp/w1041":/w -w /w "$IMG" sh -c '/opt/rocm/lib/llvm/bin/llvm-objdump -d --mcpu=gfx906 t_fdot2.o 2>/dev/null | grep -c "v_dot2_f32_f16"'
