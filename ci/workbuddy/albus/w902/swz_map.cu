// What permutation does each ds_swizzle pattern actually produce?  Dump and print the mapping.
#include <hip/hip_runtime.h>
#include <cstdio>

template <int PAT>
__device__ __forceinline__ unsigned swz(unsigned v) {
    unsigned r;
    asm volatile("ds_swizzle_b32 %0, %1 offset:%2" : "=v"(r) : "v"(v), "n"(PAT));
    return r;
}

__global__ void dump(unsigned* out, int npat) {
    const int lane = threadIdx.x & 63;
    const unsigned v = 1000u + lane;
    out[0 * 64 + lane] = swz<0x041F>(v);
    out[1 * 64 + lane] = swz<0x081F>(v);
    out[2 * 64 + lane] = swz<0x101F>(v);
    out[3 * 64 + lane] = swz<0x201F>(v);
    out[4 * 64 + lane] = swz<0x401F>(v);
    out[5 * 64 + lane] = __shfl_xor(v, 1, 32);
    out[6 * 64 + lane] = __shfl_xor(v, 16, 32);
    (void) npat;
}

int main() {
    unsigned* d = nullptr;
    hipMalloc(&d, 7 * 64 * sizeof(unsigned));
    dump<<<1, 64>>>(d, 7);
    hipDeviceSynchronize();
    unsigned h[7 * 64] = {};
    hipMemcpy(h, d, sizeof(h), hipMemcpyDeviceToHost);
    const char* name[7] = {"swz 0x041F", "swz 0x081F", "swz 0x101F", "swz 0x201F", "swz 0x401F",
                           "shfl_xor 1", "shfl_xor 16"};
    for (int p = 0; p < 7; ++p) {
        std::printf("%-12s lane0..7 ->", name[p]);
        for (int i = 0; i < 8; ++i) std::printf(" %4d", (int) (h[p * 64 + i] - 1000));
        std::printf("   | lane32..35 ->");
        for (int i = 32; i < 36; ++i) std::printf(" %4d", (int) (h[p * 64 + i] - 1000));
        std::printf("\n");
    }
    hipFree(d);
    return 0;
}
