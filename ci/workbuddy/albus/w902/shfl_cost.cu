// R55 step 1: what do the five ds_bpermute of a 32-lane butterfly actually cost?
// Same kernel shape, same register pressure ballpark, one variant exchanges lanes and one does not.
#include <hip/hip_runtime.h>
#include <cstdio>

#define REPS 64

__global__ void k_shfl(const float* in, float* out) {
    float v = in[threadIdx.x & 255];
    float acc = 0.f;
#pragma unroll
    for (int r = 0; r < REPS; ++r) {
        float s = v + (float) r;
#pragma unroll
        for (int off = 16; off > 0; off >>= 1) s += __shfl_xor(s, off, 32);
        acc += s;
    }
    out[blockIdx.x * blockDim.x + threadIdx.x] = acc;
}

__global__ void k_plain(const float* in, float* out) {
    float v = in[threadIdx.x & 255];
    float acc = 0.f;
#pragma unroll
    for (int r = 0; r < REPS; ++r) {
        float s = v + (float) r;
#pragma unroll
        for (int i = 0; i < 5; ++i) s = s * 1.0000001f + 0.25f;
        acc += s;
    }
    out[blockIdx.x * blockDim.x + threadIdx.x] = acc;
}

static float run(void (*k)(const float*, float*), const float* d_in, float* d_out, int blocks, int threads, int iters) {
    k<<<blocks, threads>>>(d_in, d_out);          // warm
    hipDeviceSynchronize();
    hipEvent_t a, b;
    hipEventCreate(&a); hipEventCreate(&b);
    hipEventRecord(a);
    for (int i = 0; i < iters; ++i) k<<<blocks, threads>>>(d_in, d_out);
    hipEventRecord(b);
    hipEventSynchronize(b);
    float ms = 0.f;
    hipEventElapsedTime(&ms, a, b);
    hipEventDestroy(a); hipEventDestroy(b);
    return ms / iters;
}

int main() {
    const int blocks = 2400, threads = 256, iters = 50;
    float *d_in = nullptr, *d_out = nullptr;
    hipMalloc(&d_in, 1024 * sizeof(float));
    hipMalloc(&d_out, (size_t) blocks * threads * sizeof(float));
    float h[1024];
    for (int i = 0; i < 1024; ++i) h[i] = 1.0f + 0.001f * i;
    hipMemcpy(d_in, h, sizeof(h), hipMemcpyHostToDevice);
    const float a = run(k_shfl, d_in, d_out, blocks, threads, iters);
    const float b = run(k_plain, d_in, d_out, blocks, threads, iters);
    std::printf("butterfly(5 shfl) %.4f ms   plain(5 fma) %.4f ms   delta %.4f ms (%.2fx)\n",
                a, b, a - b, a / b);
    std::printf("per reduction (%.2f M reductions): %.1f ns\n",
                (double) blocks * threads * 32 / 1e6 / 1.0, (a - b) * 1e6 / ((double) blocks * threads * REPS));
    hipFree(d_in); hipFree(d_out);
    return 0;
}
