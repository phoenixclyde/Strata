// tools/gfx906_dot48_selfcheck.cu - runtime proof for the two gfx906 dot cores.
//
// Compares the hardware path selected in gfx906_dot.hpp against a host-side
// scalar reference with the same signed-byte / signed-nibble contract and the
// same modulo-2^32 accumulation.  Includes edge bytes/nibbles and accumulator
// overflow (clamp=false must wrap, not saturate).
#include "strata/kernels/gfx906_dot.hpp"

#include <hip/hip_runtime.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>

static int32_t sbyte_h(uint32_t w, int i) {
    uint32_t v = (w >> (i * 8)) & 0xffu;
    return v < 0x80u ? (int32_t)v : (int32_t)v - 0x100;
}
static int32_t snibble_h(uint32_t w, int i) {
    uint32_t v = (w >> (i * 4)) & 0xfu;
    return v < 0x8u ? (int32_t)v : (int32_t)v - 0x10;
}
static int32_t ref4(int32_t a, int32_t b, int32_t c) {
    uint32_t s = (uint32_t)c;
    for (int i = 0; i < 4; ++i) s += (uint32_t)(sbyte_h((uint32_t)a, i) * sbyte_h((uint32_t)b, i));
    return (int32_t)s;
}
static int32_t ref8(int32_t a, int32_t b, int32_t c) {
    uint32_t s = (uint32_t)c;
    for (int i = 0; i < 8; ++i) s += (uint32_t)(snibble_h((uint32_t)a, i) * snibble_h((uint32_t)b, i));
    return (int32_t)s;
}

__global__ void k_flag(int* o) { o[0] = STRATA_GFX906_DOT_HW; }

__global__ void k_dot48(const int32_t* in, int32_t* o4, int32_t* o8, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    int32_t a = in[3 * i], b = in[3 * i + 1], c = in[3 * i + 2];
    o4[i] = STRATA_GFX906_DOT4(a, b, c);
    o8[i] = STRATA_GFX906_DOT8(a, b, c);
}

static uint32_t rng_state = 0x12345678u;
static uint32_t rnd() {
    rng_state ^= rng_state << 13; rng_state ^= rng_state >> 17; rng_state ^= rng_state << 5;
    return rng_state;
}

int main() {
    const int N = 8192;
    int32_t* h = (int32_t*)malloc(sizeof(int32_t) * 3 * N);
    for (int i = 0; i < N; ++i) {
        h[3 * i] = (int32_t)rnd(); h[3 * i + 1] = (int32_t)rnd(); h[3 * i + 2] = (int32_t)rnd();
    }
    // hand-picked edges: sign extremes, single-lane, and accumulator overflow
    const int32_t edges[][3] = {
        {0x7f7f7f7f, 0x7f7f7f7f, 0},
        {(int32_t)0x80808080, (int32_t)0x80808080, 0},
        {0x7f7f7f7f, (int32_t)0x80808080, 0},
        {0x0000007f, 0x0000007f, 0},
        {(int32_t)0x80000000, 0x01010101, 0},
        {0x77777777, 0x77777777, 0},
        {(int32_t)0x88888888, (int32_t)0x88888888, 0},
        {0x7f7f7f7f, 0x7f7f7f7f, 0x7ffffff0},   // must wrap with clamp=false
        {(int32_t)0x80808080, (int32_t)0x80808080, (int32_t)0x80000010},
    };
    const int NE = (int)(sizeof(edges) / sizeof(edges[0]));
    for (int i = 0; i < NE; ++i) for (int j = 0; j < 3; ++j) h[3 * i + j] = edges[i][j];

    int32_t *d_in, *d_o4, *d_o8;
    if (hipMalloc(&d_in, sizeof(int32_t) * 3 * N) != hipSuccess ||
        hipMalloc(&d_o4, sizeof(int32_t) * N) != hipSuccess ||
        hipMalloc(&d_o8, sizeof(int32_t) * N) != hipSuccess) { printf("hipMalloc failed\n"); return 2; }
    hipMemcpy(d_in, h, sizeof(int32_t) * 3 * N, hipMemcpyHostToDevice);
    k_dot48<<<(N + 127) / 128, 128>>>(d_in, d_o4, d_o8, N);
    hipError_t e = hipGetLastError();
    if (e != hipSuccess) { printf("launch: %s\n", hipGetErrorString(e)); return 3; }
    int32_t *o4 = (int32_t*)malloc(sizeof(int32_t) * N), *o8 = (int32_t*)malloc(sizeof(int32_t) * N);
    hipMemcpy(o4, d_o4, sizeof(int32_t) * N, hipMemcpyDeviceToHost);
    hipMemcpy(o8, d_o8, sizeof(int32_t) * N, hipMemcpyDeviceToHost);
    hipDeviceSynchronize();

    int bad4 = 0, bad8 = 0;
    for (int i = 0; i < N; ++i) {
        int32_t r4 = ref4(h[3 * i], h[3 * i + 1], h[3 * i + 2]);
        int32_t r8 = ref8(h[3 * i], h[3 * i + 1], h[3 * i + 2]);
        if (o4[i] != r4) { if (bad4 < 3) printf("dot4 mismatch i=%d got=%d want=%d a=%08x b=%08x c=%08x\n",
                          i, o4[i], r4, h[3*i], h[3*i+1], h[3*i+2]); ++bad4; }
        if (o8[i] != r8) { if (bad8 < 3) printf("dot8 mismatch i=%d got=%d want=%d a=%08x b=%08x c=%08x\n",
                          i, o8[i], r8, h[3*i], h[3*i+1], h[3*i+2]); ++bad8; }
    }
    // The guard is evaluated in the DEVICE compilation pass.  Printing it on
    // the host would report 0 even when the kernel uses the hardware path.
    int *d_flag, h_flag = -1;
    hipMalloc(&d_flag, sizeof(int));
    k_flag<<<1, 1>>>(d_flag);
    hipMemcpy(&h_flag, d_flag, sizeof(int), hipMemcpyDeviceToHost);
    hipDeviceSynchronize();
    printf("HW_device=%d HW_host_macro=%d N=%d edges=%d dot4_bad=%d dot8_bad=%d "
           "overflow_dot4=%d overflow_dot8=%d\n",
           h_flag, STRATA_GFX906_DOT_HW, N, NE, bad4, bad8, o4[7], o8[7]);
    hipFree(d_flag);
    hipFree(d_in); hipFree(d_o4); hipFree(d_o8); free(h); free(o4); free(o8);
    return (bad4 || bad8) ? 1 : 0;
}
