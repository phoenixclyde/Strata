// W909 probe 2: does clang -O3 fuse the EXACT code of our two dp4a shims into v_dot4?
// Shims copied verbatim from include/strata/platform/hip_compat/strata_hip.h (lines ~236-248).
typedef signed char i8;
typedef unsigned char u8;

// signed overload: uses the builtin when the arch macro is set, else the scalar fallback
__global__ void shim_signed(int *o, int a, int b, int c) {
#if defined(__gfx906__)
    *o = __builtin_amdgcn_sdot4(a, b, c, false);
#else
    const i8 *va = reinterpret_cast<const i8 *>(&a);
    const i8 *vb = reinterpret_cast<const i8 *>(&b);
    *o = c + va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2] + va[3] * vb[3];
#endif
}

// unsigned overload: the shim does NOT call udot4 - it always unrolls by hand.
__global__ void shim_unsigned(unsigned *o, unsigned a, unsigned b, unsigned c) {
    const u8 *va = reinterpret_cast<const u8 *>(&a);
    const u8 *vb = reinterpret_cast<const u8 *>(&b);
    *o = c + va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2] + va[3] * vb[3];
}

// 8-term version: would a hand-unrolled u4 dot (8 nibbles) fuse into v_dot8?
__global__ void shim_nibble8(int *o, unsigned a, unsigned b, int c) {
    int s = c;
    for (int i = 0; i < 8; ++i) {
        const int x = (int) ((a >> (4 * i)) & 0xfu) - 8;
        const int y = (int) ((b >> (4 * i)) & 0xfu) - 8;
        s += x * y;
    }
    *o = s;
}
