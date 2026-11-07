#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W1042: add the dot8 core to the header that is ACTUALLY in the compile chain.

include/strata/platform/hip_compat/strata_hip.h defines strata_dp4a / __dp4a;
the depfiles prove include/strata/hip_compat/intrinsics.hpp is NOT included by
any production TU.  The earlier attempt patched the dead header and produced a
byte-identical binary -- this patch targets the live one.
"""
import pathlib

P = pathlib.Path("/home/albus/strata166/pr/k10/include/strata/platform/hip_compat/strata_hip.h")
s = P.read_text()
anchor = "#define __dp4a strata_dp4a\n"
assert s.count(anchor) == 1, s.count(anchor)
assert "strata_dp8a" not in s, "already patched"

block = r'''
// W1042: __dp8a(a, b, c) - signed 4-bit x8 dot product on v_dot8_i32_i4.
// Nibble 0 is the least significant 4 bits.  Same modulo-2^32 accumulation
// contract as __dp4a; clamp=false means overflow WRAPS (verified with the
// 8192-case self-check in tools/gfx906_dot48_selfcheck.cu).  gfx906 has
// v_dot8_i32_i4 but NOT v_dot8c_i32_i4, so never rely on a folded "c" form.
// No production kernel calls this yet: k8v4 stores V as 4-bit codes but the
// attention probabilities are float, so using it needs a p->int4 quantiser
// and its own numeric gate (PORT_PLAN C2, R108).
static __device__ __forceinline__ int strata_dp8a(int a, int b, int c) {
#if (defined(__gfx906__) || defined(__gfx908__) || defined(__gfx90a__)) && \
    __has_builtin(__builtin_amdgcn_sdot8)
    return __builtin_amdgcn_sdot8(a, b, c, false);
#else
    int s = c;
#pragma unroll
    for (int i = 0; i < 8; ++i) {
        int x = (a >> (4 * i)) & 0xf; if (x >= 8) x -= 16;
        int y = (b >> (4 * i)) & 0xf; if (y >= 8) y -= 16;
        s += x * y;
    }
    return s;
#endif
}
#define __dp8a strata_dp8a
'''
P.write_text(s.replace(anchor, anchor + block))
print("strata_hip.h: __dp8a core added (gfx906 hardware + bit-exact fallback)")
