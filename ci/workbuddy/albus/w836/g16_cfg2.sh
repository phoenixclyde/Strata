#!/bin/bash
# W836: full configure on a fresh dir (the old one is root-owned), background, log to a file
W=/home/albus/strata166/gfx906
B=/home/albus/strata166/gfx906-b2
IMG=strata-gfx906:0.2.8p2
LOG=/home/albus/strata166/data/w836_cfg2.out
rm -rf "$B" 2>/dev/null; mkdir -p "$B"
: > "$LOG"
nohup bash -c '
docker run --rm --security-opt label=disable \
  -v '"$W"':/src -v '"$B"':/build '"$IMG"' bash -lc "
    cd /src || exit 1
    cmake -S . -B /build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DSTRATA_HIP_GFX906=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_HIP_ARCH=gfx906 \
      > /build/cfg.log 2>&1
    echo CMAKE_RC=\$?
    echo ---ROCBLAS_FOUND---
    grep -n \"rocblas\" /build/cfg.log | head -6
    echo ---CACHE_ROCBLAS---
    grep -n ROCBLAS /build/CMakeCache.txt 2>/dev/null | head -5
    echo ---W776_COUNT---
    grep -c \"STRATA_USE_HIP\" /build/build.ninja 2>/dev/null || echo nobuildninja
    echo ---CONFIGURE_TAIL---
    tail -6 /build/cfg.log
  " >> '"$LOG"' 2>&1
echo DONE >> '"$LOG"'
' >/dev/null 2>&1 &
sleep 4
echo "launched on $B"
