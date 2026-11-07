#!/bin/bash
set -u
W=~/strata166/work/r66
cd $W || exit 1

echo "=== 应用 p3 ==="
patch -p1 < /tmp/r66_p3.patch 2>&1 | tail -3

echo
echo "=== 三个开关是否都在源码里 ==="
grep -c "STRATA_PF_GROUP_SCRATCH" src/prefill/prefill.cpp
grep -c "STRATA_PREFILL_ROUTED_STREAM" src/prefill/prefill.cpp
grep -c "STRATA_PF_HC_REGION" src/prefill/prefill.cpp
ls -l include/strata/prefill/routed_stream.hpp

echo
echo "=== 增量编译（容器内，源码 /src，build /out）==="
docker run --rm -v $W:/src -v ~/strata166/gfx029-build:/out -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
    ninja -n strata 2>&1 | head -8
    echo "--- 实际编译 ---"
    time ninja strata 2>&1 | tail -25
    echo "BUILD_RC=$?"
    ls -l strata; md5sum strata
  '
