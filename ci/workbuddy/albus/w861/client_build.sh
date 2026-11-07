#!/bin/bash
# W861-AG: 编 tensilelite-client（--build-only 会跳过 LibraryLogic，真 benchmark 必须要它）
set -u
R=/home/albus/strata166
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_client_build.log
: > "$LOG"
{
echo "=== client build start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$OUTD":/out \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include
cd /out/build
echo "--- reconfigure with CLIENT=ON ---"
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/out/deps/msgpack-cxx-6.1.1" \
  -DCMAKE_CXX_FLAGS="-I$MP -DMSGPACK_ENDIAN_LITTLE_BYTE=1 -DMSGPACK_NO_BOOST=1" \
  -DCMAKE_HIP_FLAGS=-I$MP \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=ON -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=OFF \
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -Dhipblaslt_ENABLE_MXDATAGENERATOR=OFF \
  -DHIPBLASLT_ENABLE_LAZY_LOAD=ON \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include > /out/cfg_client.log 2>&1
echo "cfg rc=$?"; grep -cE "^CMake Error" /out/cfg_client.log
grep -A3 "CMake Error" /out/cfg_client.log | head -8
echo "--- build client target ---"
nice -n 19 timeout 1800 ninja tensilelite-client -j 12 2>&1 | tail -12
echo "--- 产物 ---"
find /out -name "tensilelite-client" -type f 2>/dev/null | head -3
'
echo "=== client build end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== client build start/,\$p" "$LOG" | tail -25
