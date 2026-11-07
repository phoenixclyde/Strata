// The shim's contract: a CUDA warp is a LOGICAL 32-lane half of a gfx906 wave64, so every shuffle
// defaults to width 32.  This checks the underlying width semantics on the hardware:
//   width 32 -> lane 31 of the caller's own 32-lane group (31 for the low half, 63 for the high half)
//   width 64 -> physical lane 31 for the whole wave
#include <hip/hip_runtime.h>
#include <cstdio>

__global__ void probe(int* out) {
    const int lane = threadIdx.x & 63;
    const int v = lane;
    out[threadIdx.x] = __shfl(v, 31, 32);
    out[64 + threadIdx.x] = __shfl(v, 31, 64);
}

int main() {
    int* d = nullptr;
    if (hipMalloc(&d, 2 * 64 * sizeof(int)) != hipSuccess) { std::printf("hipMalloc failed\n"); return 2; }
    probe<<<1, 64>>>(d);
    hipError_t e = hipDeviceSynchronize();
    if (e != hipSuccess) { std::printf("kernel failed: %s\n", hipGetErrorString(e)); return 3; }
    int h[128] = {};
    e = hipMemcpy(h, d, sizeof(h), hipMemcpyDeviceToHost);
    if (e != hipSuccess) { std::printf("copy failed: %s\n", hipGetErrorString(e)); return 4; }
    std::printf("lane : width32 / width64\n");
    for (int i = 0; i < 64; i += 8) {
        for (int j = i; j < i + 8; ++j) std::printf("%2d:%2d/%2d ", j, h[j], h[64 + j]);
        std::printf("\n");
    }
    (void) hipFree(d);
    return 0;
}
