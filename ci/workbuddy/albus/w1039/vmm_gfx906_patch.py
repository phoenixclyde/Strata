#!/usr/bin/env python3
"""W1039/R104: let the HIP virtual-memory path compile on the gfx906 build.

Why this is a one-condition change and not a behaviour gamble:
  * the HIP implementation already fails closed on a RUNTIME attribute
    (hipDeviceAttributeVirtualMemoryManagementSupported, vmm.cpp api());
  * the probe (albus/w1039/t_vmm.cu, run 2026-11-07 13:11) measured on this exact card:
    attribute=1, granularity 4096 B, reserve/create/map/setaccess all hipSuccess, and
    write/read + grow + give-a-chunk-back all byte-correct;
  * nothing turns on by default: --kv-grow / STRATA_KV_GROW stay the only entry points, and
    generate.cpp:6704 still requires a profile, no --batch, no --vram-elastic, one GPU.
So the compile-time exclusion was a conservative assumption about the hardware, not a fact.
"""
import io
import sys

P = "/home/albus/strata166/pr/k10/src/core/vmm.cpp"
s = io.open(P, encoding="utf-8").read()

OLD_COMMENT = """// HIP (ROCm 6+): the same elastic range through hipMemAddressReserve / hipMemCreate / hipMemMap / hipMemSetAccess.  Available
// only where the device reports virtual memory management support (STRATA_HIP_VMM=0 turns it off): --kv-grow stays off
// otherwise, as before.  Everything else (Metal, gfx906, ROCm older than 6): no virtual memory, the elastic K/V stays off.
#if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)"""

NEW_COMMENT = """// HIP (ROCm 6+): the same elastic range through hipMemAddressReserve / hipMemCreate / hipMemMap / hipMemSetAccess.  Available
// only where the device reports virtual memory management support (STRATA_HIP_VMM=0 turns it off): --kv-grow stays off
// otherwise, as before.  Everything else (Metal, ROCm older than 6): no virtual memory, the elastic K/V stays off.
// gfx906 (STRATA_HIP_GFX906, PR #638) was excluded here as "no virtual memory"; measured on an MI50 with this ROCm it
// reports hipDeviceAttributeVirtualMemoryManagementSupported = 1 and the whole reserve/create/map/access/give-back cycle
// works (albus/w1039/t_vmm.cu, W1039), so the exclusion is gone and the runtime attribute decides - which it always did.
#if defined(STRATA_USE_HIP)"""

OLD_INCLUDE = "#if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906)\n#include <hip/hip_runtime.h>"
NEW_INCLUDE = "#if defined(STRATA_USE_HIP)\n#include <hip/hip_runtime.h>"

OLD_IMPL = "#if defined(STRATA_USE_HIP) && !defined(STRATA_HIP_GFX906) && defined(HIP_VERSION_MAJOR) && HIP_VERSION_MAJOR >= 6"
NEW_IMPL = "#if defined(STRATA_USE_HIP) && defined(HIP_VERSION_MAJOR) && HIP_VERSION_MAJOR >= 6"

for old, new, tag in ((OLD_COMMENT, NEW_COMMENT, "comment+first guard"),
                      (OLD_IMPL, NEW_IMPL, "impl guard")):
    if old not in s:
        print("ANCHOR MISS:", tag)
        sys.exit(1)
    s = s.replace(old, new, 1)
    print("patched:", tag)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)

# verify the result reads the way we think it does
t = io.open(P, encoding="utf-8").read()
assert "!defined(STRATA_HIP_GFX906)" not in t, "an exclusion survived"
assert t.count("#if defined(STRATA_USE_HIP)") == 2, "expected exactly two HIP guards"
print("VERIFY: no gfx906 exclusion left in vmm.cpp; 2 HIP guards; stub branch untouched")
