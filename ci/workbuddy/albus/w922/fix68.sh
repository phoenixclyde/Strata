#!/bin/bash
set -u
W=~/strata166/work/r66
B=~/strata166/gfx029-build
LL=~/routeB/ML-gfx906/llama.cpp
cd $W || exit 1

echo "=== 补丁加的 #if 行 ==="
grep -n "^+#if defined(STRATA_USE_HIP)" /tmp/r68.patch

echo
echo "=== 改宏：单独成行的 #if defined(STRATA_USE_HIP) 加上 gfx906 ==="
grep -n "^#if defined(STRATA_USE_HIP)$" src/program/generate.cpp
sed -i 's/^#if defined(STRATA_USE_HIP)$/#if defined(STRATA_USE_HIP) || defined(STRATA_HIP_GFX906)/' src/program/generate.cpp
echo "--- 改后 ---"
grep -nE "^#if defined\(STRATA_USE_HIP\)" src/program/generate.cpp

echo
echo "=== 重编 generate.cpp.o ==="
docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
set -e
ninja -t commands CMakeFiles/strata.dir/src/program/generate.cpp.o | tail -1 > /tmp/g1.sh
time bash -e /tmp/g1.sh 2>&1 | grep -E " error |^real" | head -10
echo -n "object has the env string: "; strings CMakeFiles/strata.dir/src/program/generate.cpp.o | grep -c STRATA_SERVE_STOP_BOUND

echo "--- 链接 ---"
ninja -t commands strata | grep -E " -o strata( |$)" | tail -1 > /tmp/g2.sh
bash -e /tmp/g2.sh 2>&1 | head -20
echo "LINK_RC=$?"
ls -l strata; md5sum strata
echo -n "binary has the env string: "; strings strata | grep -c STRATA_SERVE_STOP_BOUND
' 2>&1
