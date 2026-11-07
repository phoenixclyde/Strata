# -*- coding: utf-8 -*-
"""Add the activation scales (per 32-value group) — without them the correction terms are off by s8/s4."""
p = "D:/workbuddy_space/strata_ws/albus/w947/q4k_dot8.cu"
s = open(p, encoding="utf-8").read()

s = s.replace(
"""__global__ void q4k_gemv_dp4a(const BlockQ4K * __restrict__ w, const signed char * __restrict__ xq8,
                              float * __restrict__ y, int k) {""",
"""__global__ void q4k_gemv_dp4a(const BlockQ4K * __restrict__ w, const signed char * __restrict__ xq8,
                              const float * __restrict__ s8, float * __restrict__ y, int k) {""")

s = s.replace(
"""        float sx = 0.0f;
        for (int i = 0; i < 8; i++) sx += (float) xq8[base + i];
        acc += (float) b->d * (float) sc * sumi - (float) b->dmin * (float) m * sx;""",
"""        int sx = 0;
        for (int i = 0; i < 8; i++) sx += (int) xq8[base + i];
        const float s = s8[base / 32];
        acc += (float) b->d * (float) sc * (s * (float) sumi) - (float) b->dmin * (float) m * (s * (float) sx);""")

s = s.replace(
"""__global__ void q4k_gemv_dot8(const BlockQ4K * __restrict__ w, const int * __restrict__ xq4,
                              float * __restrict__ y, int k) {""",
"""__global__ void q4k_gemv_dot8(const BlockQ4K * __restrict__ w, const int * __restrict__ xq4,
                              const float * __restrict__ s4, float * __restrict__ y, int k) {""")

s = s.replace(
"""        const int s = sdot8(q8 ^ 0x88888888u, xs, 0);   // sum (q-8)*a
        const int sumi = s + 8 * sa;                    // sum q*a
        acc += (float) b->d * (float) sc * sumi - (float) b->dmin * (float) m * (float) sa;""",
"""        const int sd = sdot8(q8 ^ 0x88888888u, xs, 0);  // sum (q-8)*a
        const int sumi = sd + 8 * sa;                   // sum q*a
        const float s = s4[base / 32];
        acc += (float) b->d * (float) sc * (s * (float) sumi) - (float) b->dmin * (float) m * (s * (float) sa);""")

s = s.replace(
"""    std::vector<signed char> xq8(K_DIM);
    std::vector<int> xq4(K_DIM / 8, 0);""",
"""    std::vector<signed char> xq8(K_DIM);
    std::vector<int> xq4(K_DIM / 8, 0);
    std::vector<float> sc8(K_DIM / 32), sc4(K_DIM / 32);""")

s = s.replace(
"""        const float s8 = mx > 0 ? mx / 127.0f : 1.0f;
        const float s4 = mx > 0 ? mx / 7.0f : 1.0f;""",
"""        const float s8 = mx > 0 ? mx / 127.0f : 1.0f;
        const float s4 = mx > 0 ? mx / 7.0f : 1.0f;
        sc8[g] = s8; sc4[g] = s4;""")

s = s.replace(
"""    BlockQ4K * dw; signed char * dx8; int * dx4; float * dy;""",
"""    BlockQ4K * dw; signed char * dx8; int * dx4; float * dy; float * ds8; float * ds4;""")

s = s.replace(
"""    hipMalloc(&dx8, K_DIM); hipMalloc(&dx4, (K_DIM / 8) * 4); hipMalloc(&dy, N_ROWS * 4);""",
"""    hipMalloc(&dx8, K_DIM); hipMalloc(&dx4, (K_DIM / 8) * 4); hipMalloc(&dy, N_ROWS * 4);
    hipMalloc(&ds8, (K_DIM / 32) * 4); hipMalloc(&ds4, (K_DIM / 32) * 4);
    hipMemcpy(ds8, sc8.data(), (K_DIM / 32) * 4, hipMemcpyHostToDevice);
    hipMemcpy(ds4, sc4.data(), (K_DIM / 32) * 4, hipMemcpyHostToDevice);""")

s = s.replace("q4k_gemv_dp4a<<<blocks, TPB>>>(dw, dx8, dy, K_DIM);", "q4k_gemv_dp4a<<<blocks, TPB>>>(dw, dx8, ds8, dy, K_DIM);")
s = s.replace("q4k_gemv_dot8<<<blocks, TPB>>>(dw, dx4, dy, K_DIM);", "q4k_gemv_dot8<<<blocks, TPB>>>(dw, dx4, ds4, dy, K_DIM);")
s = s.replace("for (int i = 0; i < rep; i++) q4k_gemv_dp4a<<<blocks, TPB>>>(dw, dx8, dy, K_DIM);",
              "for (int i = 0; i < rep; i++) q4k_gemv_dp4a<<<blocks, TPB>>>(dw, dx8, ds8, dy, K_DIM);")
s = s.replace("for (int i = 0; i < rep; i++) q4k_gemv_dot8<<<blocks, TPB>>>(dw, dx4, dy, K_DIM);",
              "for (int i = 0; i < rep; i++) q4k_gemv_dot8<<<blocks, TPB>>>(dw, dx4, ds4, dy, K_DIM);")

open(p, "w", encoding="utf-8", newline="").write(s)
print("patched, len", len(s))
