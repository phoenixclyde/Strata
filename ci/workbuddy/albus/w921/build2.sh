#!/bin/bash
set -u
B=~/strata166/gfx029-build
W=~/strata166/work/r66
LL=~/routeB/ML-gfx906/llama.cpp

docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
set -e
echo "=== 备份原产物 ==="
cp -n strata strata.bak-e0c6f250 2>/dev/null || true
md5sum strata strata.bak-e0c6f250 2>/dev/null

echo "=== 1. 编译 prefill.cpp.o ==="
ninja -t commands CMakeFiles/strata_prefill.dir/src/prefill/prefill.cpp.o | tail -1 > /tmp/c1.sh
time bash -e /tmp/c1.sh
echo "COMPILE_RC=$?"

echo "=== 2. 归档 libstrata_prefill.a ==="
ninja -t commands libstrata_prefill.a | tail -1 > /tmp/c2.sh
cut -c1-180 /tmp/c2.sh
bash -e /tmp/c2.sh
echo "AR_RC=$?"

echo "=== 3. 链接 ==="
ninja -t commands strata | tail -1 > /tmp/c3.sh
time bash -e /tmp/c3.sh
echo "LINK_RC=$?"

ls -l strata; md5sum strata
' 2>&1
