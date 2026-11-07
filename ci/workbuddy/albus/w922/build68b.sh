#!/bin/bash
set -u
W=~/strata166/work/r66
B=~/strata166/gfx029-build
LL=~/routeB/ML-gfx906/llama.cpp

docker run --rm -v $W:/src -v $B:/out -v $LL:/llama.cpp -w /out \
  strata-gfx906:0.2.9-101 bash -lc '
set -e
ninja -t commands CMakeFiles/strata.dir/src/program/generate.cpp.o | tail -1 > /tmp/g1.sh
time bash -e /tmp/g1.sh 2>&1 | grep -E " error |^real" | head -8
echo -n "object env string: "; strings CMakeFiles/strata.dir/src/program/generate.cpp.o | grep -c STRATA_SERVE_STOP_BOUND
ninja -t commands strata | grep -E " -o strata( |$)" | tail -1 > /tmp/g2.sh
bash -e /tmp/g2.sh
echo "LINK_RC=$?"
ls -l strata; md5sum strata
echo -n "binary env string: "; strings strata | grep -c STRATA_SERVE_STOP_BOUND
echo -n "serve_stop_bound 符号: "; nm -C strata 2>/dev/null | grep -c serve_stop_bound
' 2>&1
