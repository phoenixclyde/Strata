#!/bin/bash
# W836: commit each patch as its own unit so any one can be cherry-picked into an upstream PR
set -e
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1

# --- 0) save the fully-patched CMakeLists, and rebuild a W793-only version ---
cp -a CMakeLists.txt /tmp/CMakeLists.full
python3 - <<'PY'
import io, re
p = '/home/albus/strata166/pr/strata-fork/CMakeLists.txt'
s = io.open(p, encoding='utf-8').read()
start = s.find('  # [W776 local]')
if start < 0:
    raise SystemExit('W776 marker not found')
end = s.find('endif()', s.find('set_source_files_properties(src/core/dflash2.cpp', start))
end = s.find('\n', end) + 1
block = s[start:end]
assert 'STRATA_USE_HIP=1' in block and block.count('endif()') == 1, block
io.open(p, 'w', encoding='utf-8', newline='\n').write(s[:start] + s[end:])
print('W793-only: removed %d lines of W776' % block.count('\n'))
PY

echo "=== commit 1/6: W793 (rocBLAS) ==="
git add CMakeLists.txt
git commit -q -F - <<'MSG'
build(gfx906): link the rocBLAS solution table (W793)

The gfx906 branch never includes cmake/hip_backend.cmake, so
STRATA_ROCBLAS_AVAILABLE was never defined and gemm.cu's whole rocBLAS
block compiled out.  STRATA_ROCBLAS_TUNING has been set in every production
launch here and was therefore a no-op the entire time.

Evidence: the build log of the pre-fix engine carries
  gemm.hpp:96: warning: private field 'rocblas_state_' is not used
and the fixed build has zero such warnings.  Same image, only the exe
differs, ABBA x2: TTFT constant 1190 -> 915 ms (-23%), slope unchanged
(1.327 -> 1.316 ms/token); decode unaffected (46.27 tok/s before and after).

Also widens the rocBLAS guard from STRATA_ENABLE_HIP to
(STRATA_ENABLE_HIP OR STRATA_HIP_GFX906): on this branch STRATA_ENABLE_HIP
is off by design, which is why the package was never looked for.
MSG

echo "=== commit 2/6: W776 (dflash2 scope) ==="
cp -a /tmp/CMakeLists.full CMakeLists.txt
git add CMakeLists.txt
git commit -q -F - <<'MSG'
build(gfx906): scope STRATA_USE_HIP to dflash2.cpp (W776)

gfx906 builds define STRATA_HIP_GFX906 but not STRATA_USE_HIP, while
src/core/dflash2.cpp keys its CUDA-vs-HIP branches on the latter.  On this
card it therefore compiled the CUDA path, which defaults to two streams and
a high-priority stream -- the opposite of what the HIP branch does on
purpose (upstream's own comment: single stream, priority optional, measured
worse on HIP).

A global STRATA_USE_HIP was measured before and switches CUDA-only paths
elsewhere (W717/P23), so the definition is scoped to this one file.
Verified in the generated build.ninja: dflash2.cpp carries
-DSTRATA_USE_HIP=1 and no other translation unit does.
MSG

echo "=== commit 3/6: W794 (k8v4 swizzle) ==="
git add src/kernels/cuda/qsa_decode_attn.cu
git commit -q -F - <<'MSG'
gfx906: let the query swizzle cover the k8v4 KV format (W794)

The gfx906 query swizzle is a q-side LDS bijection: it permutes query
dimensions inside LDS and never touches the KV payload, so it does not
depend on the KV format.  Upstream #1661 gated it to kv_mode 1 (int8 K),
which left the production k8v4 mode (int8 K + q4_0 V) on the unswizzled
path.

Adds kv_mode 3 to both the selection predicate and the two dispatch sites.
Bit-identical selection: the permutation moves whole 16-dimension groups,
so every reduction sums the same values in the same order.
MSG

echo "=== commit 4/6: TEL-PCIE ==="
git add serve/telemetry.py
git commit -q -F - <<'MSG'
telemetry(amd): sample PCIe bandwidth and verify the card's FRU and memory

Adds three things to the AMD path, all additive:

* BW_REFRESH_S / bw(): samples gpu_pcie_rx_mb on a timer through the same
  sysfs the rest of the AMD probe uses, so the monitor can show host->GPU
  traffic that the engine itself never reports.
* name(): cross-checks the FRU string against the reported memory size and
  prefers the FRU name, which is what the card actually is on MI50-class
  parts (the marketing string there is generic).
* sample(): injects gpu_pcie_rx_mb into the metrics dict.

Kept as a merge rather than a replacement: upstream's later _loop
hardening in this same file is preserved.
MSG

echo "=== commit 5/6: W831 (monitor width) ==="
git add serve/web/app.css
git commit -q -F - <<'MSG'
web(monitor): lift the 1920px cap on the monitor page (W831)

Upstream v0.2.7.1 widened .monitor from a fixed 1240px to
min(100%, 1920px).  On a 2560-wide window that still leaves ~320px of empty
space on each side while .about and .chat stay at their own 1100px cap.

Scoped to .monitor only: .about and .chat keep upstream's 1100px, verified
by rendering both pages headless at 2560x1080.
MSG

echo "=== commit 6/6: WEB-UI (PCIe peak) ==="
git add serve/web/app.js
git commit -q -F - <<'MSG'
web(monitor): show the PCIe peak beside the live rate

The PCIe card renders the instantaneous host->GPU rate, which idles at 0.0
MB/s almost always; the interesting number is the peak reached during a
generation.  Adds a " · peak N MB/s" suffix, shown only when the sampled
peak is >= 1 MB/s so an idle card does not read "peak 0.0".

This is the only piece of our original web patch that upstream v0.2.8 does
not already implement natively: of the 78 lines that patch added, 74 are now
in upstream (images tab, API-key save, prefill rate, sampling defaults,
sparkline ceiling).  Kept in this branch under an ALBUS-W831 marker so the
patch gate can tell it apart from upstream code -- the previous marker
(saveApiKey) was a false green because upstream carries that word itself.
MSG

echo
echo "=== RESULT ==="
git log --oneline ghup/main..HEAD
echo
git status --porcelain | head -5
echo "clean if empty above"
