#!/bin/bash
B=/home/albus/strata166/gfx029-build
echo "=== cache: dirs & key flags ==="
grep -E "^CMAKE_HOME_DIRECTORY|^CMAKE_BUILD_TYPE|^CMAKE_BINARY_DIR|^STRATA_HIP_GFX906|^STRATA_ENABLE_HIP|^STRATA_HIP_ARCH|^CMAKE_CXX_COMPILER:|^CMAKE_HIP_ARCHITECTURES|^STRATA_VERIFY_MAX_T|^STRATA_HAVE_DFLASH2|^STRATA_PREFILL_MMQ" "$B/CMakeCache.txt"
echo "=== ninja: does it reference /src only, or a build path? ==="
grep -m3 "^builddir\|^  DEFINES\|^  INCLUDES" "$B/build.ninja" | cut -c1-200
grep -m2 "FLAGS = " "$B/build.ninja" | cut -c1-200
echo "=== target list (names) ==="
grep -c "^build " "$B/build.ninja"
echo "=== the engine target ==="
docker run --rm -v /home/albus/strata166/pr/strata-fork:/src -v "$B":/build strata-gfx906:0.2.9-101 bash -lc 'cd /build && ninja -t targets all 2>/dev/null | grep -E "^strata(:| )|strata_kernels" | head -8' 2>&1 | tail -10
echo "=== how many objects depend on native_mmvq.cu ==="
grep -c "native_mmvq.cu" "$B/build.ninja"
