// R55 step 2: is ds_swizzle's swap pattern the same permutation as __shfl_xor(v, n, 32), and is it faster?
// BitMode encoding (AMD GCN cross-lane doc): and_mask=offset[4:0], or_mask=offset[9:5], xor_mask=offset[14:10]
// swap groups of n  =>  offset = (n << 10) | 0x1F   (1->0x041F, 2->0x081F, 4->0x101F, 8->0x201F, 16->0x401F)
#include <hip/hip_runtime.h>
#include <cstdio>

template <int PAT>
__device__ __forceinline__ unsigned swz(unsigned v) {
    return __builtin_amdgcn_ds_swizzle(v, PAT);   // the builtin encodes the pattern correctly
}

__global__ void same(int* ok) {
    const int lane = threadIdx.x & 63;           // two 32-lane groups in one wave64
    const unsigned v = 1000u + lane;
    const int off[6] = {0, 1, 2, 4, 8, 16};
    unsigned a[6], b[6];
    a[1] = __shfl_xor(v, 1, 32);   b[1] = swz<0x041F>(v);
    a[2] = __shfl_xor(v, 2, 32);   b[2] = swz<0x081F>(v);
    a[3] = __shfl_xor(v, 4, 32);   b[3] = swz<0x101F>(v);
    a[4] = __shfl_xor(v, 8, 32);   b[4] = swz<0x201F>(v);
    a[5] = __shfl_xor(v, 16, 32);  b[5] = swz<0x401F>(v);
    int bad = 0;
    for (int i = 1; i < 6; ++i) if (a[i] != b[i]) ++bad;
    if (bad) atomicAdd(ok, 1);
    (void) off;
}

#define REPS 64
__global__ void k_shfl(const float* in, float* out) {
    float v = in[threadIdx.x & 255], acc = 0.f;
#pragma unroll
    for (int r = 0; r < REPS; ++r) {
        float s = v + (float) r;
#pragma unroll
        for (int off = 16; off > 0; off >>= 1) s += __shfl_xor(s, off, 32);
        acc += s;
    }
    out[blockIdx.x * blockDim.x + threadIdx.x] = acc;
}

__global__ void k_swz(const float* in, float* out) {
    float v = in[threadIdx.x & 255], acc = 0.f;
#pragma unroll
    for (int r = 0; r < REPS; ++r) {
        float s = v + (float) r;
        s += __uint_as_float(swz<0x401F>(__float_as_uint(s)));
        s += __uint_as_float(swz<0x201F>(__float_as_uint(s)));
        s += __uint_as_float(swz<0x101F>(__float_as_uint(s)));
        s += __uint_as_float(swz<0x081F>(__float_as_uint(s)));
        s += __uint_as_float(swz<0x041F>(__float_as_uint(s)));
        acc += s;
    }
    out[blockIdx.x * blockDim.x + threadIdx.x] = acc;
}

static float run(void (*k)(const float*, float*), const float* i, float* o, int b, int t, int n) {
    k<<<b, t>>>(i, o); hipDeviceSynchronize();
    hipEvent_t e0, e1; hipEventCreate(&e0); hipEventCreate(&e1);
    hipEventRecord(e0);
    for (int k2 = 0; k2 < n; ++k2) k<<<b, t>>>(i, o);
    hipEventRecord(e1); hipEventSynchronize(e1);
    float ms = 0.f; hipEventElapsedTime(&ms, e0, e1);
    hipEventDestroy(e0); hipEventDestroy(e1);
    return ms / n;
}

int main() {
    int* d_ok = nullptr; hipMalloc(&d_ok, sizeof(int)); hipMemset(d_ok, 0, sizeof(int));
    same<<<1, 64>>>(d_ok);
    int ok = -1; hipMemcpy(&ok, d_ok, sizeof(int), hipMemcpyDeviceToHost);
    std::printf("value mismatches over 64 lanes: %d  => %s\n", ok, ok == 0 ? "SAME permutation" : "DIFFERENT");
    const int b = 2400, t = 256, it = 50, lanes = 64;
    float *i2 = nullptr, *o2 = nullptr;
    hipMalloc(&i2, 1024 * 4); hipMalloc(&o2, (size_t) b * t * 4);
    float h[1024]; for (int j = 0; j < 1024; ++j) h[j] = 1.f + 0.001f * j;
    hipMemcpy(i2, h, sizeof(h), hipMemcpyHostToDevice);
    float a = run(k_shfl, i2, o2, b, t, it);
    float c = run(k_swz, i2, o2, b, t, it);
    std::printf("butterfly shfl %.4f ms   swizzle %.4f ms   %.1f%% faster\n", a, c, 100.0 * (a - c) / a);
    std::printf("(both are 5 exchanges + 5 adds per reduction, %d reps, %d blocks x %d threads)\n", REPS, b, t);
    hipFree(i2); hipFree(o2); hipFree(d_ok);
    (void) lanes;
    return 0;
}
