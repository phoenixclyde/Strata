#include <cuda_runtime.h>
#include "strata/hip_compat/intrinsics.hpp"
extern "C" __global__ void k_hdr(const int* a, const int* b, int* o) {
    int i = threadIdx.x;
    o[i] = ::strata::hip_compat::dp4a(a[i], b[i], 0);
}
