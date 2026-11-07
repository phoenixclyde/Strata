// include/strata/kernels/gfx906_dot.hpp - the two gfx906 integer dot cores.
//
// Vega 20 (gfx906) is the first AMD part with the VOP3P packed integer dot
// instructions.  Both take two packed i32 operands and add into a 32-bit
// accumulator; the 4th intrinsic argument selects saturating clamp, and CUDA's
// __dp4a contract (which this engine's quant kernels are written against) is
// modulo-2^32 accumulation, so clamp is always false here.
//
//   v_dot4_i32_i8 : 4 x signed int8  MACs in one instruction   (26.5 TMAC/s @60CU/1725MHz)
//   v_dot8_i32_i4 : 8 x signed int4  MACs in one instruction   (53.0 TMAC/s, 2x dot4)
//
// Verified on gfx906 (W835 / skyne98 wiki / ROCm AMDGPUAsmGFX906):
//   * BOTH instructions are available on the *specific* gfx906 target.  A
//     `gfx9-generic` build excludes them (LLVM AMDGPUUsage), so the build must
//     pass --offload-arch=gfx906 (build-masterp/build.ninja does).
//   * v_dot4c_i32_i8 / v_dot8c_i32_i4 are NOT available on gfx906; never rely
//     on the folded "c" lowering.  Clamp=false keeps the plain form.
//   * The int32 accumulator wraps on overflow with clamp=false.  Callers must
//     bound the contraction length (or split the chain) themselves.
//
// On every other target these fall back to a bit-exact scalar loop with the
// same signed-byte / signed-nibble products and the same modulo-2^32 sum, so a
// kernel written once produces identical numbers on CUDA and HIP.
#pragma once

#include <cstdint>

// Self-contained: this header is reachable from wrappers that some host-only
// translation units include with no CUDA/HIP runtime in scope, so provide the
// device qualifiers ourselves instead of depending on the includer.
#if defined(__HIP_PLATFORM_AMD__) || defined(__HIP__) || defined(__HIPCC__)
#include <hip/hip_runtime.h>
#elif defined(__CUDACC__)
#include <cuda_runtime.h>
#endif

#if defined(__HIP_DEVICE_COMPILE__) && \
    (defined(__gfx906__) || defined(__gfx908__) || defined(__gfx90a__)) && \
    __has_builtin(__builtin_amdgcn_sdot4) && __has_builtin(__builtin_amdgcn_sdot8)
#define STRATA_GFX906_DOT_HW 1
#else
#define STRATA_GFX906_DOT_HW 0
#endif

namespace strata { namespace gfx906 {

__device__ __forceinline__ int32_t sbyte(uint32_t w, int lane) {
    const uint32_t v = (w >> (lane * 8)) & 0xffu;
    return v < 0x80u ? static_cast<int32_t>(v) : static_cast<int32_t>(v) - 0x100;
}

__device__ __forceinline__ int32_t snibble(uint32_t w, int lane) {
    const uint32_t v = (w >> (lane * 4)) & 0xfu;
    return v < 0x8u ? static_cast<int32_t>(v) : static_cast<int32_t>(v) - 0x10;
}

/// dot4: 4 signed int8 MACs + int32 accumulator, modulo 2^32.
__device__ __forceinline__ int32_t dot4(int32_t a, int32_t b, int32_t c) {
#if STRATA_GFX906_DOT_HW
    return __builtin_amdgcn_sdot4(a, b, c, false);
#else
    const uint32_t ua = static_cast<uint32_t>(a), ub = static_cast<uint32_t>(b);
    uint32_t sum = static_cast<uint32_t>(c);
#pragma unroll
    for (int i = 0; i < 4; ++i)
        sum += static_cast<uint32_t>(sbyte(ua, i) * sbyte(ub, i));
    return static_cast<int32_t>(sum);
#endif
}

/// dot8: 8 signed int4 MACs + int32 accumulator, modulo 2^32.
/// Nibble 0 is the least significant 4 bits of each packed word.
__device__ __forceinline__ int32_t dot8(int32_t a, int32_t b, int32_t c) {
#if STRATA_GFX906_DOT_HW
    return __builtin_amdgcn_sdot8(a, b, c, false);
#else
    const uint32_t ua = static_cast<uint32_t>(a), ub = static_cast<uint32_t>(b);
    uint32_t sum = static_cast<uint32_t>(c);
#pragma unroll
    for (int i = 0; i < 8; ++i)
        sum += static_cast<uint32_t>(snibble(ua, i) * snibble(ub, i));
    return static_cast<int32_t>(sum);
#endif
}

}}  // namespace strata::gfx906

#define STRATA_GFX906_DOT4(a, b, c) (::strata::gfx906::dot4((a), (b), (c)))
#define STRATA_GFX906_DOT8(a, b, c) (::strata::gfx906::dot8((a), (b), (c)))
