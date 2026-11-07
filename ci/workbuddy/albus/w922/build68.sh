#!/bin/bash
set -u
W=~/strata166/work/r66
B=~/strata166/gfx029-build
LL=~/routeB/ML-gfx906/llama.cpp

echo "=== apply R68 ==="
cd $W || exit 1
patch -p1 < /tmp/r68.patch 2>&1 | tail -6
echo "--- 开关是否存在 ---"
grep -c "STRATA_SERVE_STOP_BOUND" src/program/generate.cpp
grep -c "serve_stop_bound" src/program/generate.cpp
ls -l include/strata/core/serve_stop_bound.hpp

echo
echo "=== 编译 generate.cpp.o + 链接 ==="
docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
set -e
cp -n strata strata.bak-2fa104e5 2>/dev/null || true
ninja -t commands CMakeFiles/strata.dir/src/program/generate.cpp.o | tail -1 > /tmp/g1.sh
ninja -t commands strata | tail -1 > /tmp/g2.sh
echo "--- 编译 generate.cpp.o（大文件，请等）---"
time bash -e /tmp/g1.sh 2>&1 | grep -E "error|warning: unused|^real" | head -20
echo "--- 链接 ---"
time bash -e /tmp/g2.sh
echo "--- 产物 ---"
ls -l strata; md5sum strata
strings strata | grep -c "STRATA_SERVE_STOP_BOUND"
' 2>&1
