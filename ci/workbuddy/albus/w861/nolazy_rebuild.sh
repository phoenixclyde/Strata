#!/bin/bash
# W861-L: 前台重编，抓完整错误
set -u
R=/home/albus/strata166
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$R/data/w859_hblt":/out \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out/build
nice -n 19 timeout 1500 ninja hipblaslt -j 12 2>&1 | grep -E "error:|FAILED|warning: unused" | head -25
echo "=== summary ==="
ls -la /out/build/library/libhipblaslt.so.1.4 2>/dev/null || echo MISSING
' 2>&1 | tail -30
