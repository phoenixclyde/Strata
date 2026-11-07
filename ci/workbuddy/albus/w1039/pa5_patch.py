#!/usr/bin/env python3
"""W1041 pa5: quantize the query with one warp per 64-value group (llama.cpp's quantize_q8_1 pattern).

Before: `if (t < G*NSC)` -> 48 of 256 threads, each a serial 64-element amax scan + 64 converts (~448 instr),
the other 208 threads idling at __syncthreads, repeated in all 64 blocks of every query.

After:  warp-per-group. 48 groups over 8 warps -> 6 groups per warp, 2 values per lane, amax by a full-warp
butterfly (the max is order-independent, so d and every code are bit-identical to the serial scan), then each
lane converts its own two values. ~14 instructions per group instead of 448 per thread.

Reference: llama.cpp ggml-cuda/quantize.cu quantize_q8_1 -- "one warp per 32-element block, lane k loads
x[block*32+k], a butterfly shuffle reduces the block amax, and each lane quantizes its own element".
"""
import io
import shutil

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"

OLD = """    if constexpr (OPT & 2) {
        // B1/B2: one thread per (head, 64-value group) quantizes the query the way KV_Q8's K rows are quantized:
        // q_int8 = round(q / d) with d = amax / 127.  The query is read from global, not from the (unused) fp32 tile.
        if (t < G * NSC) {
            const int h = t / NSC, g = t - h * NSC;
            const float* src = q + (size_t) (kvh * G + h) * HD + g * KV_Q8_GROUP;
            float amax = 0.0f;
#pragma unroll
            for (int j = 0; j < KV_Q8_GROUP; ++j) amax = fmaxf(amax, fabsf(src[j]));
            const float d = amax > 0.0f ? amax / 127.0f : 1.0f;
            sq8s[h][g] = d;
#pragma unroll
            for (int j = 0; j < KV_Q8_GROUP; ++j)
                sq8[h][g * KV_Q8_GROUP + j] = (int8_t) __float2int_rn(src[j] / d);
        }
        __syncthreads();
    }
"""

NEW = """    if constexpr (OPT & 2) {
        // B1/B2: the query is quantized the way KV_Q8's K rows are: q_int8 = round(q / d), d = amax / 127.
        // W1041: one WARP per (head, 64-value group) instead of one thread.  The old mapping used 48 of the 256
        // threads, each running a serial 64-element scan twice (~448 instructions) while the other 208 waited at
        // __syncthreads -- and that happened again in every one of the 64 blocks of a query, which is why the
        // dp4a path measured +6.8% instead of -35% (P447/P449).  Now: 48 groups over 8 warps, 2 values per lane,
        // amax by a butterfly.  max is order-independent, so d and every code are bit-identical to the scan.
        // Pattern copied from llama.cpp's quantize_q8_1 (one warp per block, each lane own element).
        constexpr int QPG = KV_Q8_GROUP / 32;   // 64-value group == 2 values per lane
        for (int grp = warp; grp < G * NSC; grp += WARPS) {
            const int h = grp / NSC, g = grp - h * NSC;
            const float* src = q + (size_t) (kvh * G + h) * HD + g * KV_Q8_GROUP + lane * QPG;
            float v[QPG];
#pragma unroll
            for (int j = 0; j < QPG; ++j) v[j] = src[j];
            float amax = 0.0f;
#pragma unroll
            for (int j = 0; j < QPG; ++j) amax = fmaxf(amax, fabsf(v[j]));
#pragma unroll
            for (int off = 16; off > 0; off >>= 1) amax = fmaxf(amax, __shfl_xor(amax, off));
            const float d = amax > 0.0f ? amax / 127.0f : 1.0f;
            if (lane == 0) sq8s[h][g] = d;
#pragma unroll
            for (int j = 0; j < QPG; ++j)
                sq8[h][g * KV_Q8_GROUP + lane * QPG + j] = (int8_t) __float2int_rn(v[j] / d);
        }
        __syncthreads();
    }
"""


def main():
    s = io.open(P, encoding="utf-8").read()
    assert OLD in s, "anchor missing (was pa4 applied?)"
    shutil.copy2(P, P + ".bak_pa5")
    s = s.replace(OLD, NEW, 1)
    io.open(P, "w", encoding="utf-8", newline="\n").write(s)
    print("pa5 patch applied")


if __name__ == "__main__":
    main()
