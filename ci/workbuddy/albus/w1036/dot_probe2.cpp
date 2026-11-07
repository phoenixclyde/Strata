#include <hip/hip_runtime.h>
#include <cstdint>

__device__ __forceinline__ int signed_byte(uint32_t word, int lane) {
    const unsigned value = (word >> (lane * 8)) & 0xffu;
    return value < 0x80u ? static_cast<int>(value) : static_cast<int>(value) - 0x100;
}
__device__ __forceinline__ int dp4a_portable(int a, int b, int c) {
    const uint32_t ua = static_cast<uint32_t>(a);
    const uint32_t ub = static_cast<uint32_t>(b);
    uint32_t sum = static_cast<uint32_t>(c);
#pragma unroll
    for (int lane = 0; lane < 4; ++lane)
        sum += static_cast<uint32_t>(signed_byte(ua, lane) * signed_byte(ub, lane));
    return static_cast<int>(sum);
}
extern "C" __global__ void k_real(const int* a, const int* b, int* o) {
    int i = threadIdx.x;
    o[i] = dp4a_portable(a[i], b[i], 0);
}
extern "C" __global__ void k_chain(const int* a, const int* b, int* o) {
    int i = threadIdx.x;
    int s = 0;
    s = dp4a_portable(a[i], b[i], s);
    s = dp4a_portable(a[i+1], b[i+1], s);
    s = dp4a_portable(a[i+2], b[i+2], s);
    o[i] = s;
}
