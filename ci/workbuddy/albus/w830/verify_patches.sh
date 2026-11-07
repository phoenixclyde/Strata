#!/bin/bash
# W830: gate that every local patch survived an upstream copy / rebuild.
# Run after ANY upgrade (file copy, image rebuild, binary redeploy). Exit 1 if a patch is missing.
# usage: verify_patches.sh [tree] [binary] [image]
set -u
TREE="${1:-/home/albus/strata166/src028}"
BIN="${2:-/home/albus/strata166/data/bin/strata-0.1.54n2}"
IMG="${3:-strata-gfx906:0.2.8p2}"
FAIL=0
say() { printf '  %-14s %-52s %s\n' "$1" "$2" "$3"; }

echo "== local patch gate =="
echo "   tree=$TREE"
echo "   bin=$BIN"
echo "   img=$IMG"

# 1. W793: rocBLAS wiring (two sites) + it must actually configure and link
n=$(grep -c -F "W793" "$TREE/CMakeLists.txt" 2>/dev/null || echo 0)
m=$(grep -c -F "(STRATA_ENABLE_HIP OR STRATA_HIP_GFX906) AND STRATA_ROCBLAS_AVAILABLE" "$TREE/CMakeLists.txt" 2>/dev/null || echo 0)
if [ "$n" -ge 1 ] && [ "$m" -ge 1 ]; then say W793 "CMakeLists: rocBLAS wiring" "OK"; else say W793 "CMakeLists: rocBLAS wiring" "MISSING"; FAIL=1; fi

# 2. W776: STRATA_USE_HIP scoped to dflash2.cpp (check the ninja graph, not the source)
if grep -q -F -- "-DSTRATA_USE_HIP=1" "$TREE"/build-*/build.ninja 2>/dev/null; then
  hits=$(grep -A3 -F "src/core/dflash2.cpp.o" "$TREE"/build-*/build.ninja 2>/dev/null | grep -c -F -- "-DSTRATA_USE_HIP=1")
  [ "$hits" -ge 1 ] && say W776 "ninja: dflash2.cpp built with STRATA_USE_HIP" "OK" || { say W776 "ninja: dflash2.cpp built with STRATA_USE_HIP" "MISSING"; FAIL=1; }
else
  say W776 "ninja: dflash2.cpp built with STRATA_USE_HIP" "MISSING"; FAIL=1
fi

# 3. W794: the attn swizzle/reduce12 path accepts k8v4
n=$(grep -c -F "W794" "$TREE/src/kernels/cuda/qsa_decode_attn.cu" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say W794 "qsa_decode_attn.cu" "OK" || { say W794 "qsa_decode_attn.cu" "MISSING"; FAIL=1; }

# 4. telemetry: our AMD PCIe bandwidth sampler, in the tree and in the image
n=$(grep -c -F "BW_REFRESH_S" "$TREE/serve/telemetry.py" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say TEL-PCIE "tree: BW_REFRESH_S" "OK" || { say TEL-PCIE "tree: BW_REFRESH_S" "MISSING"; FAIL=1; }
if command -v docker >/dev/null 2>&1; then
  n=$(docker run --rm "$IMG" bash -lc 'grep -c -F BW_REFRESH_S /src/serve/telemetry.py' 2>/dev/null | tr -d '\r')
  [ "${n:-0}" -ge 1 ] && say TEL-PCIE "image: BW_REFRESH_S" "OK" || { say TEL-PCIE "image: BW_REFRESH_S" "MISSING"; FAIL=1; }
fi

# 5. web UI patch.  NB: "saveApiKey" is NOT a valid marker -- upstream v0.2.8 ships it itself
#    (74 of our 78 added lines were absorbed upstream). Only the PCIe peak suffix is still ours.
n=$(grep -c -F "pciePk" "$TREE/serve/web/app.js" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say WEB-UI "tree: PCIe peak suffix" "OK" || { say WEB-UI "tree: PCIe peak suffix" "MISSING"; FAIL=1; }
if command -v docker >/dev/null 2>&1; then
  n=$(docker run --rm "$IMG" bash -lc 'grep -c -F "pciePk" /src/serve/web/app.js' 2>/dev/null | tr -d '\r')
  [ "${n:-0}" -ge 1 ] && say WEB-UI "image: PCIe peak suffix" "OK" || { say WEB-UI "image: PCIe peak suffix" "MISSING"; FAIL=1; }
fi
if command -v curl >/dev/null 2>&1; then
  n=$(curl -s --max-time 5 http://127.0.0.1:8090/web/app.js 2>/dev/null | grep -c -F "pciePk" || true)
  [ "${n:-0}" -ge 1 ] && say WEB-UI "served: PCIe peak suffix" "OK" || say WEB-UI "served: PCIe peak suffix" "WARN(engine down?)"
fi

# 5b. W831: the dashboard fills the window (upstream v0.2.7.1 caps .monitor at min(100%,1920px))
n=$(grep -c -F "ALBUS-W831" "$TREE/serve/web/app.css" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say W831 "tree: monitor fills the window" "OK" || { say W831 "tree: monitor fills the window" "MISSING"; FAIL=1; }
if command -v docker >/dev/null 2>&1; then
  n=$(docker run --rm "$IMG" bash -lc 'grep -c -F "ALBUS-W831" /src/serve/web/app.css' 2>/dev/null | tr -d '\r')
  [ "${n:-0}" -ge 1 ] && say W831 "image: monitor fills the window" "OK" || { say W831 "image: monitor fills the window" "MISSING"; FAIL=1; }
fi
if command -v curl >/dev/null 2>&1; then
  n=$(curl -s --max-time 5 http://127.0.0.1:8090/web/app.css 2>/dev/null | grep -c -F "ALBUS-W831" || true)
  [ "${n:-0}" -ge 1 ] && say W831 "served: monitor fills the window" "OK" || say W831 "served: monitor fills the window" "WARN(engine down?)"
fi

# 6. the gfx906 compat macros
n=$(grep -c -F "cudaStreamCreateWithPriority hipStreamCreateWithPriority" "$TREE/include/strata/platform/hip_compat/strata_hip.h" 2>/dev/null || echo 0)
[ "$n" -ge 1 ] && say W830-COMPAT "hip_compat stream priority macros" "OK" || { say W830-COMPAT "hip_compat stream priority macros" "MISSING"; FAIL=1; }

# 7. the deployed binary is the one we built (provenance)
if [ -f "$BIN" ]; then
  b=$(md5sum "$BIN" | cut -d' ' -f1)
  hit=$(find "$TREE" -maxdepth 2 -name strata -type f -exec md5sum {} \; 2>/dev/null | grep -c "$b" || true)
  [ "$hit" -ge 1 ] && say PROVENANCE "deployed binary matches a build artifact" "OK" || { say PROVENANCE "deployed binary matches a build artifact" "UNKNOWN"; FAIL=1; }
fi

echo
if [ "$FAIL" -eq 0 ]; then echo "GATE PASS"; else echo "GATE FAIL — do not deploy"; fi
exit "$FAIL"
