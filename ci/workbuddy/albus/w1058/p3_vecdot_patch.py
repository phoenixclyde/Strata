#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# W1058/R91-P3: wrap vec_dot_q4_K_q8_1_impl_mmq's body in an env-less compile switch
#   #if defined(STRATA_MMQ_W4A4)  -> sdot8 recenter variant (W927/W947 identity)
#   #else                         -> original body untouched (byte-identical)
# The variant consumes u bytes carrying signed int4 codes [-8,7] in the int8 container
# (a4sim/R74 layout), recenter = sdot8(q^0x88888888, a) + 8*Sigma_a, min term unchanged.
# Scratch-only: target is the build-masterp overlay copy; restored + md5-verified after.
import io
import sys

P = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/albus/strata166/build-masterp/ggml-tq-overlay/vecdotq.cuh"
s = io.open(P, encoding="utf-8").read()

key = "static __device__ __forceinline__ float vec_dot_q4_K_q8_1_impl_mmq("
i = s.find(key)
assert i >= 0, "impl not found"
assert s.find(key, i + 1) < 0, "impl not unique"
b = s.find("{", i)
depth = 0
j = b
while True:
    if s[j] == "{":
        depth += 1
    elif s[j] == "}":
        depth -= 1
        if depth == 0:
            break
    j += 1
orig_body = s[b + 1:j]

VARIANT = r"""
    // W1058/R91-P3 sdot8 recenter variant (compile with -DSTRATA_MMQ_W4A4=1).
    // Identity (W927/W947, 20000/20000): sum((q-8)*a) + 8*sum(a) == sum(q*a).
    // u bytes carry signed int4 codes [-8,7] in the int8 container (a4sim/P583 domain);
    // weight nibbles ^0x88888888 -> (q-8) as s4.  min term unchanged (Q8_1 header sum).
    float sumf_d = 0.0f;
    float sumf_m = 0.0f;

#pragma unroll
    for (int i = 0; i < QR4_K*VDR_Q4_K_Q8_1_MMQ/QI8_1; ++i) {
        int sumi_d = 0;

#pragma unroll
        for (int j = 0; j < QI8_1; j += 2) {
            const unsigned w0 = ((unsigned) v[j + 0] >> (4*i)) & 0x0F0F0F0Fu;
            const unsigned w1 = ((unsigned) v[j + 1] >> (4*i)) & 0x0F0F0F0Fu;
            const unsigned q8 =
                (((w0 >>  0) & 0xF) <<  0) | (((w0 >>  8) & 0xF) <<  4) |
                (((w0 >> 16) & 0xF) <<  8) | (((w0 >> 24) & 0xF) << 12) |
                (((w1 >>  0) & 0xF) << 16) | (((w1 >>  8) & 0xF) << 20) |
                (((w1 >> 16) & 0xF) << 24) | (((w1 >> 24) & 0xF) << 28);
            const unsigned char * ub = (const unsigned char *) &u[i*QI8_1 + j];
            const unsigned xs =
                ((unsigned) (ub[0] & 0xF) <<  0) | ((unsigned) (ub[1] & 0xF) <<  4) |
                ((unsigned) (ub[2] & 0xF) <<  8) | ((unsigned) (ub[3] & 0xF) << 12) |
                ((unsigned) (ub[4] & 0xF) << 16) | ((unsigned) (ub[5] & 0xF) << 20) |
                ((unsigned) (ub[6] & 0xF) << 24) | ((unsigned) (ub[7] & 0xF) << 28);
            const int sa8 = (int) ((signed char) ub[0]) + (int) ((signed char) ub[1])
                          + (int) ((signed char) ub[2]) + (int) ((signed char) ub[3])
                          + (int) ((signed char) ub[4]) + (int) ((signed char) ub[5])
                          + (int) ((signed char) ub[6]) + (int) ((signed char) ub[7]);
            const int sd = __builtin_amdgcn_sdot8((int) (q8 ^ 0x88888888u), (int) xs, 0, false);
            sumi_d += sd + 8 * sa8;
        }

        const float2 ds8f = __half22float2(ds8[i]);

        sumf_d += ds8f.x * (sc[i] * sumi_d);
        sumf_m += ds8f.y *   m[i];
    }

    const float2 dm4f = __half22float2(dm4);

    return dm4f.x*sumf_d - dm4f.y*sumf_m;
"""

s = s[:b + 1] + "\n#if defined(STRATA_MMQ_W4A4)" + VARIANT + "#else" + orig_body + "\n#endif\n" + s[j:]
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("PATCHED", P)
print("checks: sdot8=%d  guard=%d  orig_dp4a_line=%d" % (
    s.count("__builtin_amdgcn_sdot8"),
    s.count("#if defined(STRATA_MMQ_W4A4)"),
    s.count("sumi_d = ggml_cuda_dp4a((v[j] >> (4*i)) & 0x0F0F0F0F")))
