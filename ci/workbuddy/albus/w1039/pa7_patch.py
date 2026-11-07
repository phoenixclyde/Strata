#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1039/P457: two diagnostic OPT bits so one window can tell *which* of the three differences moves the numbers.

Why this build exists -- the confound found by reading the dispatch, not by guessing:

  production env (9 keys) has NO `STRATA_GFX906_ATTN_REDUCE12`, so the control runs
  `attn_chunk_kernel<M,false,true>` (query swizzle, **REDUCE12 = false**);
  but every OPT arm is launched by `STRATA_ATTN_OPT_SWZ` as `<M,false,true,true,O>`
  (**REDUCE12 = true**).  So every "DP4A / F16D vs control" number so far compared
  two changes at once: the dot instruction AND the packed 12-in-16 reduction.

Two new bits, both on the reduce12 path (the one the arms actually run):
  bit 4 (16) `STRATA_GFX906_ATTN_CTLREAD`  -- the baseline arithmetic (fp32 fma over the 8 dims,
                                              query from the fp32 tile) but K read through the OPT
                                              path's manual index and the 64-group scale applied
                                              once per lane.  KL == 0 here => the manual read and the
                                              late scale are innocent.
  bit 5 (32) `STRATA_GFX906_ATTN_F16Q`     -- the query rounded to fp16 and back to float, then the
                                              same fp32 fma.  Isolates "q precision" from "dot2".

Also makes the unsupported-path case loud: bits 16/32 are only implemented on the query-swizzle +
reduce12 instantiation, and if they are set without it the code prints once instead of silently
running the baseline (that is the P448 class of hole).
"""
import io

P = "/home/albus/strata166/pr/port-all/src/kernels/cuda/qsa_decode_attn.cu"
s = io.open(P, encoding="utf-8").read()
orig = s

# ---- 1. QH16: the fp16 tile is also needed by the fp32-fma arm (bit 32) ---------------------
a = "    constexpr bool F16D = (OPT & 8) != 0;                        // W1039: fp16 query, v_dot2_f32_f16 scores\n"
b = (a + "    constexpr bool QH16 = F16D || (OPT & 32) != 0;              // W1039: the fp16 query tile, also "
         "feeds the P457 fp32-fma arm\n")
assert a in s
s = s.replace(a, b, 1)

a = "    __shared__ __align__(16) __half sqh[F16D ? G : 1][HD];       // 6 KB: the query as fp16 (k stays int8)"
b = "    __shared__ __align__(16) __half sqh[QH16 ? G : 1][HD];       // 6 KB: the query as fp16 (k stays int8)"
assert a in s
s = s.replace(a, b, 1)

a = "    if constexpr (F16D) {\n        // W1039: the query as fp16."
b = "    if constexpr (QH16) {\n        // W1039: the query as fp16."
assert a in s
s = s.replace(a, b, 1)

# ---- 2. the two diagnostic branches, on the reduce12 path ------------------------------------
anchor = ("                part[h] = acc * ks;\n"
          "            }\n"
          "        } else {\n"
          "        float k8[8];\n")
assert anchor in s, "reduce12 F16D tail not found"
new = ("                part[h] = acc * ks;\n"
       "            }\n"
       "        } else if constexpr (OPT & 16) {\n"
       "            // P457 arm C: the BASELINE's arithmetic, reached through the OPT path's manual K read.\n"
       "            // load8_q8 bakes the 64-group scale into k8 and multiplies per element; here the scale is\n"
       "            // applied once per lane at the end.  Same expression, same fp32 fma, no dot instruction.\n"
       "            const uint2 kraw = *reinterpret_cast<const uint2*>(p.k_q + srow[c] * HD + lane * 8);\n"
       "            const float ks = __half2float(__ushort_as_half(p.k_scale[srow[c] * NSC + (lane * 8) / KV_Q8_GROUP]));\n"
       "            const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);\n"
       "            const int qflip = QUERY_SWIZZLE ? (lane & 4) : 0;\n"
       "#pragma unroll\n"
       "            for (int h = 0; h < G; ++h) {\n"
       "                const float4 qa = *reinterpret_cast<const float4*>(&sq[h][lane * 8 + qflip]);\n"
       "                const float4 qb = *reinterpret_cast<const float4*>(&sq[h][lane * 8 + (qflip ^ 4)]);\n"
       "                const float pp = (float) kb[0] * qa.x + (float) kb[1] * qa.y + (float) kb[2] * qa.z +\n"
       "                                 (float) kb[3] * qa.w + (float) kb[4] * qb.x + (float) kb[5] * qb.y +\n"
       "                                 (float) kb[6] * qb.z + (float) kb[7] * qb.w;\n"
       "                part[h] = pp * ks;\n"
       "            }\n"
       "        } else if constexpr (OPT & 32) {\n"
       "            // P457 arm D: the query rounded to fp16 and back to float, then the same fp32 fma.\n"
       "            // Only the input is rounded -- no dot2, no scale change -- so it isolates q precision.\n"
       "            const uint2 kraw = *reinterpret_cast<const uint2*>(p.k_q + srow[c] * HD + lane * 8);\n"
       "            const float ks = __half2float(__ushort_as_half(p.k_scale[srow[c] * NSC + (lane * 8) / KV_Q8_GROUP]));\n"
       "            const int8_t* kb = reinterpret_cast<const int8_t*>(&kraw);\n"
       "            float kf[8];\n"
       "#pragma unroll\n"
       "            for (int j = 0; j < 8; ++j) kf[j] = (float) kb[j] * ks;\n"
       "#pragma unroll\n"
       "            for (int h = 0; h < G; ++h) {\n"
       "                float pp = 0.0f;\n"
       "#pragma unroll\n"
       "                for (int j = 0; j < 8; ++j) pp += __half2float(sqh[h][lane * 8 + j]) * kf[j];\n"
       "                part[h] = pp;\n"
       "            }\n"
       "        } else {\n"
       "        float k8[8];\n")
s = s.replace(anchor, new, 1)

# ---- 3. env wiring: bits 16 / 32 -------------------------------------------------------------
a = '        const char* d = std::getenv("STRATA_GFX906_ATTN_F16D");   // W1039: bit 3, fp16 query + v_dot2_f32_f16\n'
b = (a +
     '        const char* e = std::getenv("STRATA_GFX906_ATTN_CTLREAD");  // W1039/P457: bit 4, baseline arithmetic\n'
     '        const char* f = std::getenv("STRATA_GFX906_ATTN_F16Q");     // W1039/P457: bit 5, fp16 query + fp32 fma\n')
assert a in s
s = s.replace(a, b, 1)

a = '        if (d && d[0] == \'1\') o |= 8;\n'
b = (a +
     '        if (e && e[0] == \'1\') o |= 16;\n'
     '        if (f && f[0] == \'1\') o |= 32;\n')
assert a in s
s = s.replace(a, b, 1)

# ---- 4. switch cases on the swizzle dispatcher only ------------------------------------------
a = ("#define STRATA_ATTN_OPT_DISPATCH_SWZ(LAUNCH, M)                                                           \\\n"
     "    switch (opt_sw) {                                                                                     \\\n")
assert a in s
i = s.index(a) + len(a)
j = s.index("        default: break;", i)
add = ("        case 16: LAUNCH(M, 16); break;                                                                    \\\n"
       "        case 32: LAUNCH(M, 32); break;                                                                    \\\n")
s = s[:j] + add + s[j:]

# ---- 5. make the unsupported combination loud instead of silently running the baseline --------
a = ("    if (const int opt = gfx906_attn_opt();\n"
     "        opt != 0 && !lane_cell && !use_query_swizzle && (kv_mode == 3 || kv_mode == 1)) {\n")
b = ("#if defined(STRATA_HIP_GFX906)\n"
     "    if ((gfx906_attn_opt() & 48) != 0 && !use_query_swizzle) {   // P457: bits 16/32 live on the swizzle path\n"
     "        static thread_local bool said = false;\n"
     "        if (!said) { said = true;\n"
     "            std::fprintf(stderr, \"strata attn-opt: bits 16/32 need the query-swizzle path; running the baseline\\n\"); }\n"
     "    }\n"
     "#endif\n"
     "    if (const int opt = gfx906_attn_opt();\n"
     "        opt != 0 && (opt & 48) == 0 && !lane_cell && !use_query_swizzle && (kv_mode == 3 || kv_mode == 1)) {\n")
assert a in s
s = s.replace(a, b, 1)

a = ("    if (const int opt = (kernel < 0 ? gfx906_attn_opt() : 0); opt != 0 && !lane_cell && (kv_mode == 3 || kv_mode == 1)) {\n")
b = ("    if (const int opt = (kernel < 0 ? gfx906_attn_opt() : 0);\n"
     "        opt != 0 && (opt & 48) == 0 && !lane_cell && (kv_mode == 3 || kv_mode == 1)) {\n")
assert a in s
s = s.replace(a, b, 1)

assert s != orig
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("pa7 patched:")
for t in ("QH16", "OPT & 16", "OPT & 32", "ATTN_CTLREAD", "case 16:", "opt & 48"):
    print("   %-14s x%d" % (t, s.count(t)))
