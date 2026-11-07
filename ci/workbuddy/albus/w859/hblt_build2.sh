#!/bin/bash
# W859-B：编 hipBLASLt 主机库（gfx906），配置已通过；只编库，不跑 profile 目标
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_hblt_build2.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== build2 start $(date +%F" "%T)"
  docker run --rm --name strata-w859b2 -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
cd /out/build
echo "--- 目标里带 hipblaslt 的:"
ninja -t targets all 2>/dev/null | grep -E "^lib?hipblaslt|^hipblaslt:" | head -6
echo "--- 开始编 $(date +%H:%M:%S)"
timeout 2400 nice -n 10 ninja -j 14 hipblaslt 2>&1 | tail -25
echo "--- ninja rc=$?  $(date +%H:%M:%S)"
find /out/build -name "libhipblaslt.so*" -o -name "librocblaslt.so*" | head -5
ls -l /out/build/library 2>/dev/null | head -5
'
  echo "=== build2 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
grep -E "目标里|开始编|ninja rc|libhipblaslt|librocblaslt|build2 end|error:" "$LOG" | tail -20
