#!/usr/bin/env python3
# W1050 R114: port a dot2 variant of gdn_ab_kernel behind STRATA_GFX906_GDN_DOT2.
# Original kernel untouched (off arm preserved).  Microbench evidence (gdn_ab_bench):
# dot2 5.75us vs fmaf 7.65us per call = 1.33x, rel_rms 2.1e-4 on synthetic data.
# Site is latency/occupancy-bound (12 blocks/call, 65 GB/s << HBM roofline), which is
# why the ALU swap pays despite the conversion cost.
import io
import shutil

P = "/home/albus/strata166/pr/k10/src/kernels/cuda/fused_gdn.cu"
s = io.open(P, encoding="utf-8").read()
shutil.copy2(P, "/home/albus/strata166/tmp/w1050/fused_gdn.cu.orig")
orig = s

# 1. header
a = '#include "fused_gdn.cuh"'
if a not in s:
    # find first include
    i = s.find("#include")
    j = s.find("\n", i) + 1
    s = s[:j] + '#include <hip/hip_fp16.h>   // W1050/R114: __half2 for the v_dot2_f32_f16 GDN ab path\n' + s[j:]
else:
    s = s.replace(a, a + '\n#include <hip/hip_fp16.h>   // W1050/R114: __half2 for the v_dot2_f32_f16 GDN ab path', 1)

# 2. dot2 helper + dot2 kernel after the existing gdn_ab_kernel (before the closing namespace)
anchor = "}  // namespace"
idx = s.find(anchor)   # FIRST close: the anonymous ns holding gdn_ab_kernel (rfind lands after the launch site)
assert idx > 0
new = r'''
// W1050/R114 B4: the same gdn_ab math with v_dot2_f32_f16.  Weights stay bf16 in memory;
// per-iteration they are widened to fp32 and narrowed to fp16 alongside the fp32 activation
// (the KI dense_gemv preconverts weights for reuse; this kernel reads each weight once per
// call so conversion is inline).  Microbench gdn_ab_bench.cu: 1.33x over the fmaf arm.
__device__ __forceinline__ float gdn_dot2(float acc, uint32_t a, uint32_t b) {
    asm volatile("v_dot2_f32_f16 %0, %1, %2, %3" : "+v"(acc) : "v"(a), "v"(b));
    return acc;
}
__global__ void __launch_bounds__(256) gdn_ab_kernel_dot2(const float* __restrict__ x, const uint16_t* __restrict__ wa,
                                                          const uint16_t* __restrict__ wb, const float* __restrict__ dt,
                                                          const float* __restrict__ ssm_a, float* __restrict__ gate,
                                                          float* __restrict__ beta, int n, int h_v) {
    const int row = blockIdx.x * 8 + (threadIdx.x >> 5), lane = threadIdx.x & 31;
    if (row >= 2 * h_v) return;
    const bool is_beta = row >= h_v;
    const int r = is_beta ? row - h_v : row;
    const uint4* w4 = reinterpret_cast<const uint4*>((is_beta ? wb : wa) + (size_t) r * n);
    float acc = 0.0f;
    for (int j = lane; j < n / 8; j += 32) {
        const uint4 wv = __ldg(w4 + j);
        const float4 xa = *reinterpret_cast<const float4*>(x + j * 8);
        const float4 xb = *reinterpret_cast<const float4*>(x + j * 8 + 4);
        float wf[8];
        wf[0] = __uint_as_float(wv.x << 16);         wf[1] = __uint_as_float(wv.x & 0xffff0000u);
        wf[2] = __uint_as_float(wv.y << 16);         wf[3] = __uint_as_float(wv.y & 0xffff0000u);
        wf[4] = __uint_as_float(wv.z << 16);         wf[5] = __uint_as_float(wv.z & 0xffff0000u);
        wf[6] = __uint_as_float(wv.w << 16);         wf[7] = __uint_as_float(wv.w & 0xffff0000u);
        float xf[8] = {xa.x, xa.y, xa.z, xa.w, xb.x, xb.y, xb.z, xb.w};
        uint32_t wp[4], ap[4];
#pragma unroll
        for (int k = 0; k < 4; ++k) {
            const __half2 wh = __halves2half2(__float2half(wf[2 * k]), __float2half(wf[2 * k + 1]));
            const __half2 ah = __halves2half2(__float2half(xf[2 * k]), __float2half(xf[2 * k + 1]));
            wp[k] = *reinterpret_cast<const uint32_t*>(&wh);
            ap[k] = *reinterpret_cast<const uint32_t*>(&ah);
        }
        acc = gdn_dot2(acc, wp[0], ap[0]); acc = gdn_dot2(acc, wp[1], ap[1]);
        acc = gdn_dot2(acc, wp[2], ap[2]); acc = gdn_dot2(acc, wp[3], ap[3]);
    }
    for (int o = 16; o > 0; o >>= 1) acc += __shfl_xor_sync(0xffffffffu, acc, o);
    if (lane != 0) return;
    if (is_beta) {
        beta[r] = 1.0f / (1.0f + __expf(-acc));
    } else {
        const float v = acc + dt[r];
        const float sp = v > 20.0f ? v : log1pf(__expf(v));
        gate[r] = sp * ssm_a[r];
    }
}

'''
s = s[:idx] + new + s[idx:]

# 3. launch switch in fused_gdn_ab
old_launch = "    gdn_ab_kernel<<<(unsigned) ((2 * h_v + 7) / 8), 256, 0, (cudaStream_t) stream>>>(x, w_alpha, w_beta, dt, ssm_a, gate,"
SHORT = "gdn_ab_kernel<<<"
assert s.count(SHORT) == 1, s.count(SHORT)
i = s.find(SHORT)
i = s.rfind("\n", 0, i) + 1
# find the end of the launch statement
j = s.find(";", i) + 1
launch_stmt = s[i:j]
new_launch = ("    static const bool gdn_dot2_on = [] {\n"
              "        const char* e = std::getenv(\"STRATA_GFX906_GDN_DOT2\");\n"
              "        return e != nullptr && e[0] == '1';\n"
              "    }();\n"
              "    if (gdn_dot2_on) {\n"
              "        gdn_ab_kernel_dot2<<<(unsigned) ((2 * h_v + 7) / 8), 256, 0, (cudaStream_t) stream>>>(x, w_alpha, w_beta, dt, ssm_a, gate,\n"
              "                                 beta, n_embd, h_v);\n"
              "    } else {\n"
              + launch_stmt.replace("    gdn_ab_kernel<<<", "        gdn_ab_kernel<<<").replace("\n", "\n        ") + "\n"
              "    }")
s = s[:i] + new_launch + s[j:]

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched fused_gdn.cu", len(orig), "->", len(s))
