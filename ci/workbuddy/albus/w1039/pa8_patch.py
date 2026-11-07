#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: pa8 = pa7 + one device-side print in the bit-16 arm.

Why: C16 is *supposed* to be the baseline's arithmetic, only read through `p.k_q`/`p.k_scale` by hand.
It came back at KL 0.04111 while pa7's control is bit-identical to b12180 -- and the four switch arms
carry errors that are the same size but only 0.5-0.65 correlated, which is not what one wrong index
would look like.  So instead of another hypothesis, print the evidence: for block(0,0,0), warp 0,
lanes 0 and 7, print the raw K codes and the scale as the manual path reads them, the dequantised
values `load8<KV_MODE>` returns for the same (row, d0), and both dot results.

  manual == load8*scale  and  dot_manual == dot_load8  ->  the read and the arithmetic are innocent,
                                                            the divergence is somewhere else
  they differ                                          ->  the read (or the scale index) is wrong
"""
import io

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()

anchor = ("            const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);\n"
          "            const int qflip = QUERY_SWIZZLE ? (lane & 4) : 0;\n"
          "#pragma unroll\n"
          "            for (int h = 0; h < G; ++h) {\n"
          "                const float4 qa = *reinterpret_cast<const float4*>(&sq[h][lane * 8 + qflip]);\n"
          "                const float4 qb = *reinterpret_cast<const float4*>(&sq[h][lane * 8 + (qflip ^ 4)]);\n"
          "                const float pp = (float) kb[0] * qa.x + (float) kb[1] * qa.y + (float) kb[2] * qa.z +\n"
          "                                 (float) kb[3] * qa.w + (float) kb[4] * qb.x + (float) kb[5] * qb.y +\n"
          "                                 (float) kb[6] * qb.z + (float) kb[7] * qb.w;\n"
          "                part[h] = pp * ks;\n"
          "            }\n")
assert anchor in s, "bit-16 branch not found"

dbg = ("            const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);\n"
       "            const int qflip = QUERY_SWIZZLE ? (lane & 4) : 0;\n"
       "#pragma unroll\n"
       "            for (int h = 0; h < G; ++h) {\n"
       "                const float4 qa = *reinterpret_cast<const float4*>(&sq[h][lane * 8 + qflip]);\n"
       "                const float4 qb = *reinterpret_cast<const float4*>(&sq[h][lane * 8 + (qflip ^ 4)]);\n"
       "                const float pp = (float) kb[0] * qa.x + (float) kb[1] * qa.y + (float) kb[2] * qa.z +\n"
       "                                 (float) kb[3] * qa.w + (float) kb[4] * qb.x + (float) kb[5] * qb.y +\n"
       "                                 (float) kb[6] * qb.z + (float) kb[7] * qb.w;\n"
       "                part[h] = pp * ks;\n"
       "                if (h == 0 && blockIdx.x == 0 && blockIdx.y == 0 && blockIdx.z == 0 &&\n"
       "                    (lane == 0 || lane == 7)) {\n"
       "                    float r8[8];\n"
       "                    load8<KV_MODE>(p, false, srow[c], lane * 8, r8);\n"
       "                    const float sref = r8[0] * qa.x + r8[1] * qa.y + r8[2] * qa.z + r8[3] * qa.w +\n"
       "                                       r8[4] * qb.x + r8[5] * qb.y + r8[6] * qb.z + r8[7] * qb.w;\n"
       "                    printf(\"DBG16 row=%lld lane=%d ks=%.9g codes=[%d %d %d %d %d %d %d %d] \"\n"
       "                           \"load8=[%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f] \"\n"
       "                           \"part0=%.9g sref=%.9g rel=%.3g\\n\",\n"
       "                           srow[c], (int) lane, ks,\n"
       "                           (int) kb[0], (int) kb[1], (int) kb[2], (int) kb[3],\n"
       "                           (int) kb[4], (int) kb[5], (int) kb[6], (int) kb[7],\n"
       "                           r8[0], r8[1], r8[2], r8[3], r8[4], r8[5], r8[6], r8[7],\n"
       "                           part[h], sref, fabsf(part[h] - sref) / (fabsf(sref) + 1e-12f));\n"
       "                }\n"
       "            }\n")
s = s.replace(anchor, dbg, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("pa8 instrumented: bit-16 prints manual vs load8 for lanes 0 and 7")
