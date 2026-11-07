#!/usr/bin/env python3
# W839-19 幂等：把 W839 的调用块插进指定 generate.cpp（用于构建树）
import io, sys

P = sys.argv[1]
MARK = "// [W839 local]"

BLOCK = '''#if defined(STRATA_HIP_GFX906)
    {   // [W839 local] The per-architecture defaults table never reached a gfx906 build.  The call in the
        // HIP block above sits under `#if defined(STRATA_USE_HIP)`, and this build defines only
        // STRATA_HIP_GFX906 (W717/P23: a global STRATA_USE_HIP switches CUDA-only paths elsewhere, so it
        // stays scoped to dflash2.cpp).  Consequence: arch_defaults.cpp was linked into no executable, and
        // neither STRATA_GFX906_ATTN_REDUCE12 nor the rest of the table could ever apply.  Same contract as
        // the other builds: every visible card is the same architecture, and a switch the user set is kept.
        // STRATA_GFX906_DEFAULTS=0 turns the table off (arch_defaults.cpp reads it).
        cudaDeviceProp ad{};
        if (cudaGetDeviceProperties(&ad, 0) == cudaSuccess) {
            bool all_igpu = ad.integrated != 0;   // a discrete MI50: false
            int ndev = 0;
            if (all_igpu && cudaGetDeviceCount(&ndev) == cudaSuccess) {
                for (int d = 1; d < ndev && d < 64; ++d) {
                    cudaDeviceProp od{};
                    if (cudaGetDeviceProperties(&od, d) != cudaSuccess || od.integrated == 0 ||
                        std::strncmp(od.gcnArchName, ad.gcnArchName, 7) != 0) { all_igpu = false; (void) cudaGetLastError(); break; }
                }
            }
            strata::core::apply_arch_defaults(ad.gcnArchName, all_igpu);
        } else (void) cudaGetLastError();
    }
#endif
'''

ANCHOR = "#if defined(STRATA_HIP_GFX906)\n    {   // #1728: the gfx906 build's kernels assume 64-lane waves"

s = io.open(P, encoding="utf-8").read()
if MARK in s:
    print("already patched:", P)
    sys.exit(0)
n = s.count(ANCHOR)
print("anchor count =", n)
if n != 1:
    print("ANCHOR NOT UNIQUE -- abort"); sys.exit(2)
s2 = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("patched %s  %d -> %d" % (P, len(s), len(s2)))
