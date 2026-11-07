#include <hip/hip_runtime.h>
#include <cstdint>
extern "C" __global__ void k_dot(const int* a, const int* b, int* o) {
    int i = threadIdx.x;
    o[i] = __builtin_amdgcn_sdot4(a[i], b[i], 0, false);
}
extern "C" __global__ void k_emul(const int* a, const int* b, int* o) {
    int i = threadIdx.x;
    unsigned ua = (unsigned)a[i], ub = (unsigned)b[i];
    unsigned sum = 0;
    #pragma unroll
    for (int l = 0; l < 4; ++l) {
        int sa = (int)((signed char)((ua >> (8*l)) & 0xff));
        int sb = (int)((signed char)((ub >> (8*l)) & 0xff));
        sum += (unsigned)(sa * sb);
    }
    o[i] = (int)sum;
}
