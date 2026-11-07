# -*- coding: utf-8 -*-
"""Add a host-side simulation of the exact dp4a kernel loop for (token 0, row 0), so we can tell
'formula/data bug' from 'kernel indexing bug' without guessing."""
p = "D:/workbuddy_space/strata_ws/albus/w947/q4k_gemm_dot8.cu"
s = open(p, encoding="utf-8").read()

anchor = "    BlockQ4K * dw; signed char * dx8; int * dx4, *dsx8, *dsa4; float * ds8, *ds4, *dy;"
assert anchor in s

sim = r'''    // ---- host simulation of the dp4a kernel (token 0, row 0), same formula, no GPU ----
    {
        double sim = 0.0;
        const BlockQ4K * wr = &w[0];
        for (int base = 0; base < K_DIM; base += 8) {
            const BlockQ4K * b = wr + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m; get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned q8 = pack8_u4(b->qs + 16 * j, g);
            int sumi = 0;
            for (int i = 0; i < 8; i++) sumi += (int) ((q8 >> (4 * i)) & 0xF) * (int) xq8[base + i];
            const float s = sc8[base / 32];
            const int sx = sx8[base / 8];
            sim += (double) ((float) b->d * sc * (s * (float) sumi) - (float) b->dmin * m * (s * (float) sx));
        }
        printf("HOST-SIM (token0,row0) = %.6f   fp32-ref = %.6f   ratio = %.6f\n",
               sim, ref[0], ref[0] != 0 ? sim / ref[0] : 0.0);

        // and the same for the dot8 path
        double sim8 = 0.0;
        for (int base = 0; base < K_DIM; base += 8) {
            const BlockQ4K * b = wr + base / QK_K;
            const int kk = base % QK_K, j = kk / 32, g = (kk % 32) / 8;
            unsigned char sc, m; get_scale_min_k4(j, b->scales, &sc, &m);
            const unsigned qx = pack8_u4(b->qs + 16 * j, g) ^ 0x88888888u;
            int sd = 0;
            for (int i = 0; i < 8; i++) {
                const int q = (int) ((qx >> (4 * i)) & 0xF);
                const int qs4 = (q >= 8) ? q - 16 : q;          // s4 interpretation
                const int xa = (int) ((xq4[base / 8] >> (4 * i)) & 0xF);
                const int xs4 = (xa >= 8) ? xa - 16 : xa;
                sd += qs4 * xs4;
            }
            const int sa = sa4[base / 8];
            const int sumi = sd + 8 * sa;
            const float s = sc4[base / 32];
            sim8 += (double) ((float) b->d * sc * (s * (float) sumi) - (float) b->dmin * m * (s * (float) sa));
        }
        printf("HOST-SIM-DOT8 (token0,row0) = %.6f   fp32-ref = %.6f   ratio = %.6f\n",
               sim8, ref[0], ref[0] != 0 ? sim8 / ref[0] : 0.0);
    }

'''
s = s.replace(anchor, sim + anchor)
open(p, "w", encoding="utf-8", newline="").write(s)
print("patched, len", len(s))
