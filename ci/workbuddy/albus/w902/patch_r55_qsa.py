"""R55 phase 2a: route the 32-lane XOR exchanges of qsa_select.cu through ds_swizzle.

`__shfl_xor(v, n, 32)` compiles to ds_bpermute_b32 (address VGPR + LDS bank traffic, W902: 2.74x the
cost of the same arithmetic).  ds_swizzle_b32's swap patterns produce the SAME lane permutation
(W902: 0 mismatches at n = 1, 2, 4, 8, 16, both halves of the wave64), with the pattern in the
instruction and no address.  The override is TU-local so nothing else has to be rebuilt; the header
rollout is a separate step after this one is measured.
"""
import shutil
import sys
from pathlib import Path

P = Path('/home/albus/strata166/work/r55/src/kernels/cuda/qsa_select.cu')
BAK = P.with_suffix('.cu.r55bak')
if not BAK.exists():
    shutil.copy2(P, BAK)

src = P.read_text(encoding='utf-8')

# insert right after the last #include of the file's include block
anchor = None
for line in src.splitlines():
    if line.startswith('#include'):
        anchor = line
if anchor is None:
    print('no include found')
    sys.exit(2)

helper = anchor + '''

// [R55] 32-lane XOR exchanges through ds_swizzle_b32.  Its swap-n pattern is the same permutation as
// __shfl_xor(v, n, 32) - verified lane by lane on gfx906 in W902 (0 mismatches, n = 1, 2, 4, 8, 16,
// including the second 32-lane half of the wave64) - but the pattern lives in the instruction, so there
// is no address VGPR and no LDS bank traffic.  Anything else falls back to the shim's __shfl_xor.
// STRATA_NO_SHFL_SWIZZLE=1 at compile time keeps the old path for an A/B.
#if defined(__HIPCC__) && !defined(STRATA_NO_SHFL_SWIZZLE)
namespace strata_r55 {
template <typename T>
__device__ __forceinline__ T swz_xor(T v, int n) {
    union { T t; unsigned u; } in, out;
    in.t = v;
    switch (n) {
        case 1:  out.u = __builtin_amdgcn_ds_swizzle(in.u, 0x041F); break;
        case 2:  out.u = __builtin_amdgcn_ds_swizzle(in.u, 0x081F); break;
        case 4:  out.u = __builtin_amdgcn_ds_swizzle(in.u, 0x101F); break;
        case 8:  out.u = __builtin_amdgcn_ds_swizzle(in.u, 0x201F); break;
        case 16: out.u = __builtin_amdgcn_ds_swizzle(in.u, 0x401F); break;
        default: out.t = __shfl_xor(v, n, 32); break;
    }
    return out.t;
}
}  // namespace strata_r55
#undef __shfl_xor_sync
#define __shfl_xor_sync(mask, var, n, ...) strata_r55::swz_xor((var), (n))
#endif
'''

if 'strata_r55::swz_xor' in src:
    print('already patched')
    sys.exit(0)

# put it after the LAST include line, not the first (headers must be complete first)
idx = 0
for i, line in enumerate(src.splitlines(True)):
    if line.startswith('#include'):
        idx = i
lines = src.splitlines(True)
new = ''.join(lines[: idx + 1]) + helper + ''.join(lines[idx + 1 :])
P.write_text(new, encoding='utf-8')
print('patched qsa_select.cu after include line', idx + 1)
