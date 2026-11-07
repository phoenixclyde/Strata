#!/bin/bash
set -u
W=~/strata166/work/r66
B=~/strata166/gfx029-build
LL=~/routeB/ML-gfx906/llama.cpp

docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
set -e
echo "=== generate.cpp.o 是否更新 ==="
ls -l CMakeFiles/strata.dir/src/program/generate.cpp.o
strings CMakeFiles/strata.dir/src/program/generate.cpp.o | grep -c STRATA_SERVE_STOP_BOUND || true

echo
echo "=== 精确取链接命令（含 -o strata）==="
ninja -t commands strata | grep -E " -o strata( |$)" | tail -1 > /tmp/g2.sh
head -c 200 /tmp/g2.sh; echo

echo "=== 执行链接 ==="
time bash -e /tmp/g2.sh

echo
echo "=== 产物 ==="
ls -l strata; md5sum strata
echo -n "STRATA_SERVE_STOP_BOUND in binary: "; strings strata | grep -c STRATA_SERVE_STOP_BOUND
' 2>&1
