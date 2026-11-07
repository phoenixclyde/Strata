#!/bin/bash
# W859-B：把 src/msgpack/MessagePack.cpp 加进 tensilelite-host（相对路径，无变量、无引号陷阱）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_mp3.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== build start $(date +%F" "%T)"
  docker run --rm -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
F=/src/projects/hipblaslt/tensilelite/CMakeLists.txt
if grep -q W859MP $F; then
  echo "  already patched"
else
  sed -i "/add_library(tensilelite-host)/a\    target_sources(tensilelite-host PRIVATE src/msgpack/MessagePack.cpp)  # W859MP" $F
  echo "  patched"
fi
grep -n W859MP $F | head -2
cd /out/build
cmake . > /out/cfg10.log 2>&1; echo "  cmake rc=$?"
nice -n 19 timeout 900 ninja -j 6 hipblaslt 2>&1 | tail -5
echo "--- .a msgpack 符号数:"; nm -C tensilelite/libtensilelite-host.a 2>/dev/null | grep -ci msgpack
echo "--- .so 未定义 TensileLite 符号:"; nm -C library/libhipblaslt.so.1 2>/dev/null | grep " U .*TensileLite" | head -3
'
  echo "=== build end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== build start/,\$p" "$LOG" | tail -12
