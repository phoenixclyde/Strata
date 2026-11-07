#!/bin/bash
# W836: does the branch actually configure? (rocBLAS must be found -> W793 landed on upstream's tree)
W=/home/albus/strata166/gfx906
IMG=strata-gfx906:0.2.8p2
echo "=== A. configure the branch tree in a throwaway build dir ==="
rm -rf /home/albus/strata166/gfx906-build && mkdir -p /home/albus/strata166/gfx906-build
docker run --rm --security-opt label=disable \
  -v "$W":/src -v /home/albus/strata166/gfx906-build:/build \
  -v /home/albus/strata166/data:/data \
  "$IMG" bash -lc '
    cd /src || exit 1
    cmake -S . -B /build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DSTRATA_HIP_GFX906=ON \
      -DSTRATA_ENABLE_HIP=OFF \
      -DSTRATA_HIP_ARCH=gfx906 \
      > /build/cfg.log 2>&1
    echo "cmake rc=$?"
    echo "--- rocBLAS decision (W793) ---"
    grep -nE "rocblas|ROCBLAS|gfx906 rocBLAS" /build/cfg.log | head -8
    echo "--- would the macro be defined? ---"
    grep -n "STRATA_ROCBLAS_AVAILABLE" /build/CMakeCache.txt 2>/dev/null | head -3
    echo "--- dflash2 scope (W776) ---"
    grep -n "STRATA_USE_HIP" /build/build.ninja 2>/dev/null | head -3
    echo "--- configure tail ---"
    tail -4 /build/cfg.log
  ' 2>&1 | tail -30
