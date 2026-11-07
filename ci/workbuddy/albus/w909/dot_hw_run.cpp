// W909 probe 3: run v_dot4_i32_i8 and v_dot8_i32_i4 ON THE MI50 and check the numbers.
// The LLVM docs table for the gfx9-generic processor claims v_dot* are "not available on gfx906"
// while the gfx906 assembler page lists them; a real launch settles it.
#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstdlib>

__global__ void run_sdot4(int *out, int a, int b, int c) { out[0] = __builtin_amdgcn_sdot4(a, b, c, false); }
__global__ void run_sdot8(int *out, int a, int b, int c) { out[0] = __builtin_amdgcn_sdot8(a, b, c, false); }
__global__ void run_fdot2(float *out, _Float16 a0, _Float16 a1, _Float16 b0, _Float16 b1, float c) {
    typedef _Float16 f16x2 __attribute__((ext_vector_type(2)));
    const f16x2 a = {a0, a1};
    const f16x2 b = {b0, b1};
    out[0] = __builtin_amdgcn_fdot2(a, b, c, false);
}

static void chk(const char *w) {
    const hipError_t e = hipGetLastError();
    if (e != hipSuccess) {
        std::printf("%s FAILED: %s\n", w, hipGetErrorString(e));
        std::exit(1);
    }
}

int main() {
    int *d = nullptr;
    if (hipMalloc(&d, 4) != hipSuccess) { std::printf("no device\n"); return 1; }

    // sdot4: bytes {1,2,3,4} . {5,6,7,8} + 10 = 5+12+21+32+10 = 80
    const int a4 = 0x04030201, b4 = 0x08070605;
    int h = 0;
    run_sdot4<<<1, 1>>>(d, a4, b4, 10); chk("sdot4");
    hipMemcpy(&h, d, 4, hipMemcpyDeviceToHost);
    std::printf("sdot4  = %d (expect 80)   %s\n", h, h == 80 ? "OK" : "MISMATCH");

    // sdot8: nibbles of a = {1,2,3,4,5,6,7,8}, b = {1,1,1,1,1,1,1,1}; sum=36, +0 -> 36
    const int a8 = 0x87654321, b8 = 0x11111111;
    run_sdot8<<<1, 1>>>(d, a8, b8, 0); chk("sdot8");
    hipMemcpy(&h, d, 4, hipMemcpyDeviceToHost);
    std::printf("sdot8  = %d (expect 36)   %s\n", h, h == 36 ? "OK (hardware has v_dot8_i32_i4)" : "MISMATCH");

    // negative nibble check: a nibbles = {-1,-1,-1,-1,-1,-1,-1,-1} = 0xFFFFFFFF, b = 1 each -> -8
    run_sdot8<<<1, 1>>>(d, 0xFFFFFFFF, 0x11111111, 0); chk("sdot8 neg");
    hipMemcpy(&h, d, 4, hipMemcpyDeviceToHost);
    std::printf("sdot8- = %d (expect -8)   %s\n", h, h == -8 ? "OK signed i4" : "MISMATCH");

    float f = 0.0f;
    run_fdot2<<<1, 1>>>(reinterpret_cast<float *>(d), (_Float16) 1.5f, (_Float16) 2.0f, (_Float16) 3.0f, (_Float16) 4.0f, 1.0f);
    chk("fdot2");
    hipMemcpy(&f, d, 4, hipMemcpyDeviceToHost);
    std::printf("fdot2  = %.2f (expect 13.50) %s\n", f, (f > 13.49f && f < 13.51f) ? "OK" : "MISMATCH");
    return 0;
}
