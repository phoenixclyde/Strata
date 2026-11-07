#!/bin/bash
# W859-B：带 msgpack-cxx 头重配 + 重编 hipBLASLt 主机库（gfx906）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_hblt_build4.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== build3 start $(date +%F" "%T)"
  docker run --rm --name strata-w859b3 -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include
ls $MP/msgpack.hpp || exit 1
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/opt/rocm/hip;/opt/rocm/llvm" \
  -DCMAKE_CXX_FLAGS="-I$MP -DMSGPACK_NO_BOOST" \
  -DCMAKE_HIP_FLAGS="-I$MP -DMSGPACK_NO_BOOST" \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DHIPBLASLT_ENABLE_CLIENT=OFF \
  -DHIPBLASLT_ENABLE_YAML=ON -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF -DHIPBLASLT_ENABLE_ASAN=OFF \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include \
  > /out/cfg2.log 2>&1
echo "--- configure rc=$?"
[ -f /out/build/build.ninja ] || { tail -12 /out/cfg2.log; exit 1; }
cd /out/build
echo "--- 编译 $(date +%H:%M:%S)"
timeout 2400 nice -n 10 ninja -j 14 hipblaslt 2>&1 | tail -22
echo "--- ninja done $(date +%H:%M:%S)"
find /out/build -name "libhipblaslt.so*" | head -3
ls -l /out/build/library/src/amd_detail/*.so* 2>/dev/null | head -3
'
  echo "=== build3 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
grep -E "configure rc|编译|ninja done|libhipblaslt|build3 end|error:|FAILED" "$LOG" | tail -14
