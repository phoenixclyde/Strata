// R55 step 0: what does a 32-lane butterfly actually compile to on gfx906?
// The shim maps __shfl_xor_sync(mask, v, o) -> __shfl_xor(v, o, 32), so this is exactly the code the
// kernels run.  Count ds_bpermute_b32 (LDS roundtrip) against v_mov_dpp / ds_swizzle_b32.
#include <hip/hip_runtime.h>

__global__ void butterfly32(const float* in, float* out) {
    float v = in[threadIdx.x];
#pragma unroll
    for (int off = 16; off > 0; off >>= 1) v += __shfl_xor(v, off, 32);
    out[threadIdx.x] = v;
}

// the same amount of arithmetic without any lane exchange (the floor)
__global__ void noexchange(const float* in, float* out) {
    float v = in[threadIdx.x];
#pragma unroll
    for (int i = 0; i < 5; ++i) v = v * 1.000001f + 0.5f;
    out[threadIdx.x] = v;
}
