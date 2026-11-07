// Same question, but through LLVM's own intrinsic instead of hand-written asm encoding.
#include <hip/hip_runtime.h>
#include <cstdio>

template <int PAT>
__device__ __forceinline__ unsigned swzb(unsigned v) {
    return __builtin_amdgcn_ds_swizzle(v, PAT);
}

__global__ void dump(unsigned* out) {
    const int lane = threadIdx.x & 63;
    const unsigned v = 1000u + lane;
    out[0 * 64 + lane] = swzb<0x041F>(v);
    out[1 * 64 + lane] = swzb<0x081F>(v);
    out[2 * 64 + lane] = swzb<0x101F>(v);
    out[3 * 64 + lane] = swzb<0x201F>(v);
    out[4 * 64 + lane] = swzb<0x401F>(v);
    out[5 * 64 + lane] = __shfl_xor(v, 1, 32);
    out[6 * 64 + lane] = __shfl_xor(v, 2, 32);
    out[7 * 64 + lane] = __shfl_xor(v, 4, 32);
    out[8 * 64 + lane] = __shfl_xor(v, 8, 32);
    out[9 * 64 + lane] = __shfl_xor(v, 16, 32);
}

int main() {
    unsigned* d = nullptr;
    hipMalloc(&d, 10 * 64 * sizeof(unsigned));
    dump<<<1, 64>>>(d);
    hipDeviceSynchronize();
    unsigned h[10 * 64] = {};
    hipMemcpy(h, d, sizeof(h), hipMemcpyDeviceToHost);
    const char* name[10] = {"swzb 0x041F", "swzb 0x081F", "swzb 0x101F", "swzb 0x201F", "swzb 0x401F",
                            "shfl 1", "shfl 2", "shfl 4", "shfl 8", "shfl 16"};
    for (int p = 0; p < 10; ++p) {
        std::printf("%-12s ->", name[p]);
        for (int i = 0; i < 8; ++i) std::printf(" %3d", (int) (h[p * 64 + i] - 1000));
        std::printf("  | hi:");
        for (int i = 32; i < 36; ++i) std::printf(" %3d", (int) (h[p * 64 + i] - 1000));
        std::printf("\n");
    }
    // equivalence check
    int bad[5] = {};
    for (int k = 0; k < 5; ++k)
        for (int i = 0; i < 64; ++i)
            if (h[k * 64 + i] != h[(5 + k) * 64 + i]) ++bad[k];
    std::printf("mismatch per pattern (1,2,4,8,16): %d %d %d %d %d\n", bad[0], bad[1], bad[2], bad[3], bad[4]);
    hipFree(d);
    return 0;
}
