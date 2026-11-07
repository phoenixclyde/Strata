// W909: which dot instructions does OUR toolchain (AMD clang 24 / ROCm 7.14) emit for gfx906?
// Device-only probe: every kernel is a single expression so the disassembly maps 1:1 to an instruction.
#include <hip/hip_runtime.h>

// --- signed 8-bit dot: the "dp4a" our strata_dp4a(int,int,int) shim uses ---
__global__ void k_sdot4(int *o, int a, int b, int c) { *o = __builtin_amdgcn_sdot4(a, b, c, false); }
// --- unsigned 8-bit dot: what our strata_dp4a(unsigned,unsigned,unsigned) overload does NOT use ---
__global__ void k_udot4(unsigned *o, unsigned a, unsigned b, unsigned c) {
    *o = __builtin_amdgcn_udot4(a, b, c, false);
}
// --- 4-bit x 4-bit dot (8 elements per 32-bit word) ---
__global__ void k_sdot8(int *o, int a, int b, int c) { *o = __builtin_amdgcn_sdot8(a, b, c, false); }
__global__ void k_udot8(unsigned *o, unsigned a, unsigned b, unsigned c) {
    *o = __builtin_amdgcn_udot8(a, b, c, false);
}
// --- fp16 pair dot into f32 (V_DOT2_F32_F16) ---
typedef _Float16 f16x2 __attribute__((ext_vector_type(2)));
__global__ void k_fdot2(float *o, f16x2 a, f16x2 b, float c) {
    *o = __builtin_amdgcn_fdot2(a, b, c, false);
}
// --- control: plain scalar 4x multiply-add, i.e. what a macro fallback would look like.
// Question: does -O3 pattern-match this into v_dot4 by itself?
__global__ void k_scalar(int *o, int a, int b, int c) {
    const signed char *va = (const signed char *) &a;
    const signed char *vb = (const signed char *) &b;
    *o = c + va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2] + va[3] * vb[3];
}
