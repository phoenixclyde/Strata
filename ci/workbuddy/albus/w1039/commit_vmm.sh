#!/bin/bash
# W1039: commit the vmm change so strata-0.1.57-kvg (a85743d7) is reproducible from a sha.
set -u
cd /home/albus/strata166/pr/k10 || exit 1
git status --porcelain | head -5
git add src/core/vmm.cpp
git -c user.name=albus -c user.email=albus@localhost commit -q -F - <<'EOF'
gfx906: compile the HIP virtual-memory path (the elastic K/V, --kv-grow)

The HIP implementation was excluded on gfx906 by `!defined(STRATA_HIP_GFX906)`, with the comment
"gfx906: no virtual memory". Measured on this MI50 with this ROCm (10.1.0, self-built gfx906 tree):

  hipDeviceAttributeVirtualMemoryManagementSupported = 1
  hipMemGetAllocationGranularity = 4096 B
  hipMemAddressReserve(64 MiB) / hipMemCreate / hipMemMap / hipMemSetAccess -> all hipSuccess
  two chunks mapped at different offsets: write/read both correct
  after unmap + release of one chunk the other still reads back correctly  <- what --kv-grow needs

So the exclusion was an assumption about the hardware, not a fact.  It is also redundant: the
implementation already fails closed on the runtime attribute, and nothing turns the elastic K/V on
by itself (--kv-grow / STRATA_KV_GROW plus generate.cpp's eleven conditions).

Also note the guard has to be an OR: this tree's gfx906 TUs get -DSTRATA_HIP_GFX906=1 but NOT
-DSTRATA_USE_HIP (build.ninja, every target but dflash2.cpp), so `#if defined(STRATA_USE_HIP)` alone
compiles the stub again and the binary does not change at all (md5 stayed d24f8293 on the first try).

Probe: albus/w1039/t_vmm.cu.  Ledger: P472 (probe), P473 (the silent no-op), P474 (candidate).
EOF
git log --oneline -2
echo "SHA=$(git rev-parse --short HEAD)"
