#!/usr/bin/env python3
# apply_w839_generate.py -- idempotent W839 hunk for src/program/generate.cpp
#
# Why a patch script instead of a file copy: the branch tracks upstream main, the build tree tracks
# v0.2.8, and generate.cpp differs between those two by hundreds of upstream lines.  Copying the whole
# file would drag upstream's later changes into a v0.2.8 build.  So the sync copies only files that are
# identical between the two bases, and applies this hunk by anchor for the ones that are not.
#
# Usage: apply_w839_generate.py [path-to-generate.cpp]   (default: the build tree)
import io, sys

P = sys.argv[1] if len(sys.argv) > 1 else "/home/albus/strata166/src028/src/program/generate.cpp"
MARK = "// [W839 local]"

BLOCK = '''#if defined(STRATA_HIP_GFX906)
    {   // [W839 local] The per-architecture defaults table never reached a gfx906 build.  The call in the
        // HIP block above sits under `#if defined(STRATA_USE_HIP)`, and this build defines only
        // STRATA_HIP_GFX906 (W717/P23: a global STRATA_USE_HIP switches CUDA-only paths elsewhere, so it
        // stays scoped to dflash2.cpp).  Consequence: arch_defaults.cpp was linked into no executable, and
        // neither STRATA_GFX906_ATTN_REDUCE12 nor the rest of the table could ever apply.  Same contract as
        // the other builds: every visible card is the same architecture, and a switch the user set is kept.
        // STRATA_GFX906_DEFAULTS=0 turns the table off (arch_defaults.cpp reads it).
        // STRATA_W839_TRACE=1 prints the device probe, which is how "the call never ran" was told apart
        // from "it ran and set nothing".
        cudaDeviceProp ad{};
        const cudaError_t rc = cudaGetDeviceProperties(&ad, 0);
        if (std::getenv("STRATA_W839_TRACE") != nullptr)
            std::fprintf(stderr, "strata: [W839] device probe rc=%d name=%s\\n", (int) rc,
                         rc == cudaSuccess ? ad.gcnArchName : "-");
        if (rc == cudaSuccess) {
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
    print("apply_w839_generate: already applied (%s)" % P)
    sys.exit(0)
n = s.count(ANCHOR)
if n != 1:
    print("apply_w839_generate: ANCHOR COUNT %d != 1 -- refusing (%s)" % (n, P))
    sys.exit(2)
io.open(P, "w", encoding="utf-8", newline="\n").write(s.replace(ANCHOR, BLOCK + ANCHOR, 1))
print("apply_w839_generate: applied to %s" % P)
