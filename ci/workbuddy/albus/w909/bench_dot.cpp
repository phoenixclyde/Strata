// W909 probe 4: achieved MAC/s of v_dot4_i32_i8 vs v_dot8_i32_i4 on this MI50, ILP4.
// Every lane runs ITER iterations of 4 independent chains, so the result is VALU-bound, not memory-bound.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>

#define ITER 20000

__global__ void bench_dot4(int *out, int seed) {
    int a0 = seed, a1 = seed + 1, a2 = seed + 2, a3 = seed + 3;
    int b = seed * 7 + 1;
    int s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (int i = 0; i < ITER; ++i) {
        s0 = __builtin_amdgcn_sdot4(a0, b, s0, false);
        s1 = __builtin_amdgcn_sdot4(a1, b, s1, false);
        s2 = __builtin_amdgcn_sdot4(a2, b, s2, false);
        s3 = __builtin_amdgcn_sdot4(a3, b, s3, false);
    }
    if (s0 + s1 + s2 + s3 == 12345678) out[0] = s0;   // never true: keeps the loop alive
}

__global__ void bench_dot8(int *out, int seed) {
    int a0 = seed, a1 = seed + 1, a2 = seed + 2, a3 = seed + 3;
    int b = seed * 7 + 1;
    int s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (int i = 0; i < ITER; ++i) {
        s0 = __builtin_amdgcn_sdot8(a0, b, s0, false);
        s1 = __builtin_amdgcn_sdot8(a1, b, s1, false);
        s2 = __builtin_amdgcn_sdot8(a2, b, s2, false);
        s3 = __builtin_amdgcn_sdot8(a3, b, s3, false);
    }
    if (s0 + s1 + s2 + s3 == 12345678) out[0] = s0;
}

template <typename F>
static double run(F k, int blocks, int threads, int cu) {
    int *d = nullptr;
    hipMalloc(&d, 4);
    k<<<blocks, threads>>>(d, 3);          // warm-up
    hipDeviceSynchronize();
    hipEvent_t t0, t1;
    hipEventCreate(&t0);
    hipEventCreate(&t1);
    hipEventRecord(t0);
    for (int r = 0; r < 3; ++r) k<<<blocks, threads>>>(d, 3);
    hipEventRecord(t1);
    hipEventSynchronize(t1);
    float ms = 0.0f;
    hipEventElapsedTime(&ms, t0, t1);
    hipFree(d);
    const double insn = 3.0 * (double) blocks * threads * ITER * 4.0;   // 4 chains per lane
    return insn / (ms * 1e-3) / 1e9;                                    // G instr/s
}

int main() {
    hipDeviceProp_t p{};
    hipGetDeviceProperties(&p, 0);
    const int cu = p.multiProcessorCount;
    const int threads = 256;                       // 4 waves of 64
    const int blocks = cu * 8;
    std::printf("device %s  CUs=%d  clock=%.0f MHz\n", p.name, cu, p.clockRate / 1000.0);

    const double i4 = run(bench_dot4, blocks, threads, cu);
    const double i8 = run(bench_dot8, blocks, threads, cu);
    std::printf("ideal per CU = 64 lanes * 1 instr/clk * %.3f GHz = %.2f Ginstr/s per CU, %.2f total\n",
                p.clockRate / 1e6, 64.0 * p.clockRate / 1e6, 64.0 * cu * p.clockRate / 1e6);
    std::printf("sdot4 : %.2f Ginstr/s -> %.2f TMAC/s  (%.0f%% of the 4-MAC peak)\n", i4, i4 * 4 / 1000.0,
                100.0 * i4 / (64.0 * cu * p.clockRate / 1e6));
    std::printf("sdot8 : %.2f Ginstr/s -> %.2f TMAC/s  (%.0f%% of the 8-MAC peak)\n", i8, i8 * 8 / 1000.0,
                100.0 * i8 / (64.0 * cu * p.clockRate / 1e6));
    std::printf("dot8/dot4 instruction ratio = %.2fx\n", i8 / i4);
    return 0;
}
