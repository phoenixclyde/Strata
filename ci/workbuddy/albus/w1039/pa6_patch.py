#!/usr/bin/env python3
"""W1039 pa6: a third score path -- fp16 query + v_dot2_f32_f16 (OPT bit 3 = 8).

Why: int8 (OPT bit 1) is fast but its step (amax/127 ~ 1.3% of sigma_q ~ 0.1 nat of score) lands on the model's
own top1-top2 margin (median 0.191 nat), so it costs 6.45% of the argmax (P453/P454).  fp16 keeps 2 MAC per
instruction and needs no epilogue beyond one scale multiply, so it should be as fast while being ~40x more accurate
(2^-11 = 0.049% vs 1.3%).

k stays int8 in memory: |k| <= 127 is exact in fp16, and the KV scale is applied after the dot.
"""
import io
import shutil

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"

INC_OLD = '#include "strata/kernels/dp4a.hpp"'
INC_NEW = '#include "strata/kernels/dp4a.hpp"\n#include <hip/hip_fp16.h>   // W1039: __half2 for the v_dot2_f32_f16 score path'

CONST_OLD = """    __shared__ float sq8s[(OPT & 2) ? G : 1][NSC];               // one scale per (head, 64-value group)"""
CONST_NEW = CONST_OLD + """
    constexpr bool F16D = (OPT & 8) != 0;                        // W1039: fp16 query, v_dot2_f32_f16 scores
    __shared__ __align__(16) __half sqh[F16D ? G : 1][HD];       // 6 KB: the query as fp16 (k stays int8)"""

QUANT_OLD = """    __syncthreads();
    if constexpr (LANE_CELL) {"""
QUANT_NEW = """    if constexpr (F16D) {
        // W1039: the query as fp16.  No scale, no per-group amax -- one convert per element, all threads.
        for (int i = t; i < G * HD; i += THREADS)
            sqh[i / HD][i % HD] = __float2half(q[(size_t) (kvh * G) * HD + i]);
    }
    __syncthreads();
    if constexpr (LANE_CELL) {"""

# --- score branch 1 (REDUCE12)
B1_OLD = """                part[h] = dot8_dp4a((int) kraw.x, (int) kraw.y, &sq8[h][lane * 8], sq8s[h][lane >> 3], ks);
        } else {"""
B1_NEW = """                part[h] = dot8_dp4a((int) kraw.x, (int) kraw.y, &sq8[h][lane * 8], sq8s[h][lane >> 3], ks);
        } else if constexpr (F16D) {
            const uint2 kraw = *reinterpret_cast<const uint2*>(p.k_q + srow[c] * HD + lane * 8);
            const float ks = __half2float(__ushort_as_half(p.k_scale[srow[c] * NSC + (lane * 8) / KV_Q8_GROUP]));
            const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);
            __half2 kh[4];
#pragma unroll
            for (int j = 0; j < 4; ++j) kh[j] = __floats2half2_rn((float) kb[2 * j], (float) kb[2 * j + 1]);
#pragma unroll
            for (int h = 0; h < G; ++h) {
                float acc = 0.0f;
#pragma unroll
                for (int j = 0; j < 4; ++j)
                    acc = __builtin_amdgcn_fdot2(*reinterpret_cast<const __half2*>(&sqh[h][lane * 8 + 2 * j]), kh[j], acc, false);
                part[h] = acc * ks;
            }
        } else {"""

# --- score branch 2 (per-head warp_sum)
B2_OLD = """                float s = dot8_dp4a((int) kraw.x, (int) kraw.y, &sq8[h][lane * 8], sq8s[h][lane >> 3], ks);
                s = warp_sum(s, (OPT & 1) != 0);
                if (lane == 0) sp[h][c] = s * scale;
            }
        } else {"""
B2_NEW = """                float s = dot8_dp4a((int) kraw.x, (int) kraw.y, &sq8[h][lane * 8], sq8s[h][lane >> 3], ks);
                s = warp_sum(s, (OPT & 1) != 0);
                if (lane == 0) sp[h][c] = s * scale;
            }
        } else if constexpr (F16D) {
            const uint2 kraw = *reinterpret_cast<const uint2*>(p.k_q + srow[c] * HD + lane * 8);
            const float ks = __half2float(__ushort_as_half(p.k_scale[srow[c] * NSC + (lane * 8) / KV_Q8_GROUP]));
            const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);
            __half2 kh[4];
#pragma unroll
            for (int j = 0; j < 4; ++j) kh[j] = __floats2half2_rn((float) kb[2 * j], (float) kb[2 * j + 1]);
#pragma unroll
            for (int h = 0; h < G; ++h) {
                float acc = 0.0f;
#pragma unroll
                for (int j = 0; j < 4; ++j)
                    acc = __builtin_amdgcn_fdot2(*reinterpret_cast<const __half2*>(&sqh[h][lane * 8 + 2 * j]), kh[j], acc, false);
                float s = acc * ks;
                s = warp_sum(s, (OPT & 1) != 0);
                if (lane == 0) sp[h][c] = s * scale;
            }
        } else {"""

# --- dispatch: add 8/9 to both switches
D1_OLD = """        case 7: LAUNCH(M, 7); break;                                                                      \\
        default: break;                                                                                   \\
    }"""
D1_NEW = """        case 7: LAUNCH(M, 7); break;                                                                      \\
        case 8: LAUNCH(M, 8); break;                                                                      \\
        case 9: LAUNCH(M, 9); break;                                                                      \\
        default: break;                                                                                   \\
    }"""


def main():
    s = io.open(P, encoding="utf-8").read()
    shutil.copy2(P, P + ".bak_pa6")
    n = 0
    for old, new in ((INC_OLD, INC_NEW), (CONST_OLD, CONST_NEW), (QUANT_OLD, QUANT_NEW),
                     (B1_OLD, B1_NEW), (B2_OLD, B2_NEW)):
        assert old in s, "anchor missing: " + old[:60]
        s = s.replace(old, new, 1)
        n += 1
    assert D1_OLD in s
    s = s.replace(D1_OLD, D1_NEW)          # both switch macros
    print("dispatch cases added:", s.count("case 8: LAUNCH"))
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("pa6 patch applied, anchors:", n)


if __name__ == "__main__":
    main()
