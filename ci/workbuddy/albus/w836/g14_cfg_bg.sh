#!/bin/bash
# W836: background configure check (container cmake takes minutes)
W=/home/albus/strata166/gfx906
IMG=strata-gfx906:0.2.8p2
LOG=/home/albus/strata166/data/w836_cfg.out
: > "$LOG"
rm -rf /home/albus/strata166/gfx906-build && mkdir -p /home/albus/strata166/gfx906-build
nohup bash -c '
  docker run --rm --security-opt label=disable \
    -v /home/albus/strata166/gfx906:/src -v /home/albus/strata166/gfx906-build:/build \
    '"$IMG"' bash -lc "
      cd /src || exit 1
      cmake -S . -B /build -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DSTRATA_HIP_GFX906=ON -DSTRATA_ENABLE_HIP=OFF -DSTRATA_HIP_ARCH=gfx906 \
        > /build/cfg.log 2>&1
      echo CMAKE_RC=\$?
      echo ---ROCBLAS---
      grep -nE \"rocblas|ROCBLAS\" /build/cfg.log | head -10
      echo ---CACHE---
      grep -n STRATA_ROCBLAS_AVAILABLE /build/CMakeCache.txt 2>/dev/null | head -3
      echo ---W776---
      grep -c STRATA_USE_HIP /build/build.ninja 2>/dev/null
      echo ---TAIL---
      tail -5 /build/cfg.log
    " > '"$LOG"' 2>&1
  echo DONE >> '"$LOG"'
' >/dev/null 2>&1 &
sleep 5
echo "launched; log=$LOG"
tail -2 "$LOG" 2>/dev/null
