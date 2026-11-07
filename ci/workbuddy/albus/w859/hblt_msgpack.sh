#!/bin/bash
# W859-B：补 TENSILE_MSGPACK（LoadLibraryMapping 的定义在 #ifdef TENSILE_MSGPACK 里，
#          而 hipblaslt 无条件引用它 —— YAML-only 构建必然缺符号）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_msgpack.log
IMG=strata-gfx906:0.2.9-101
: > "$LOG"
{
  echo "=== msgpack build start $(date +%F" "%T)"
  docker run --rm -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/opt/rocm/hip;/opt/rocm/llvm" \
  -DCMAKE_CXX_FLAGS="-I$MP -DMSGPACK_NO_BOOST -DTENSILE_MSGPACK" \
  -DCMAKE_HIP_FLAGS="-I$MP -DMSGPACK_NO_BOOST -DTENSILE_MSGPACK" \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=ON -DHIPBLASLT_ENABLE_EXTOPS=OFF \
  -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include \
  > /out/cfg8.log 2>&1
echo "  cmake rc=$?"
cd /out/build && nice -n 19 timeout 900 ninja -j 6 hipblaslt 2>&1 | tail -5
echo "--- .a 里的符号:"; nm -C tensilelite/libtensilelite-host.a 2>/dev/null | grep -c "LoadLibraryMapping"
echo "--- .so 里的符号:"; nm -C library/libhipblaslt.so.1 2>/dev/null | grep "LoadLibraryMapping" | head -1
'
  echo "=== msgpack build end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== msgpack build start/,\$p" "$LOG" | tail -12
