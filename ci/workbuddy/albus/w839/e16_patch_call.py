#!/usr/bin/env python3
# W839-16 在分支上：给 gfx906 构建补上 apply_arch_defaults 的调用点
import io, sys, os

P = "/home/albus/strata166/gfx906/src/program/generate.cpp"
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
    print("already patched")
    sys.exit(0)

n = s.count(ANCHOR)
print("anchor count =", n)
if n != 1:
    print("ANCHOR NOT UNIQUE -- abort")
    sys.exit(2)

s2 = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
assert s2 != s
io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("patched; file size %d -> %d" % (len(s), len(s2)))

# 自检
chk = io.open(P, encoding="utf-8").read()
assert chk.count("apply_arch_defaults") >= 1
i = chk.find(MARK)
print("context:")
print(chk[i-120:i+260])
