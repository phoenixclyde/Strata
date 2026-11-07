#!/usr/bin/env python3
"""W1039/R104 patch v2 — the gfx906 TU has -DSTRATA_HIP_GFX906=1 but NOT -DSTRATA_USE_HIP.

build.ninja (build-masterp, vmm.cpp.o):
    DEFINES = ... -DSTRATA_HIP_GFX906=1 ... -D__HIP_PLATFORM_AMD__=1
    INCLUDES = -I/src/include -isystem .../hip_compat -isystem /opt/rocm/include

So the guard must be (STRATA_USE_HIP || STRATA_HIP_GFX906).  v1 only removed the gfx906 exclusion
and left `#if defined(STRATA_USE_HIP)` -> false -> the stub compiled again and the binary did not
change at all (md5 d24f8293, 0 occurrences of "HIP virtual memory").  Caught by strings, not by
a window.
"""
import io
import sys

P = "/home/albus/strata166/pr/k10/src/core/vmm.cpp"
s = io.open(P, encoding="utf-8").read()

pairs = [
    ("#if defined(STRATA_USE_HIP)\n#include <hip/hip_runtime.h>",
     "#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)\n#include <hip/hip_runtime.h>",
     "include block"),
    ("#if defined(STRATA_USE_HIP) && defined(HIP_VERSION_MAJOR) && HIP_VERSION_MAJOR >= 6",
     "#if (defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)) && defined(HIP_VERSION_MAJOR) && HIP_VERSION_MAJOR >= 6",
     "implementation block"),
]
for old, new, tag in pairs:
    if old not in s:
        print("ANCHOR MISS:", tag)
        sys.exit(1)
    s = s.replace(old, new, 1)
    print("patched:", tag)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)

t = io.open(P, encoding="utf-8").read()
assert t.count("defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)") == 2
assert "&& !defined(STRATA_HIP_GFX906) && !defined(STRATA_GPU_METAL)" in t   # the CUDA branch keeps it
print("VERIFY: 2 HIP guards now include gfx906; CUDA branch unchanged")
