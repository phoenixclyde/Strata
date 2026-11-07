#!/bin/bash
# W861-AH: 造 shared/mxdatagenerator 占位目录（clients/common:31 无条件 add_subdirectory），再编 client
set -u
R=/home/albus/strata166
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_client_build2.log
: > "$LOG"
{
echo "=== client2 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$OUTD":/out \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include

echo "--- 占位 mxdatagenerator ---"
D=/src/shared/mxdatagenerator
mkdir -p "$D"
cat > "$D/CMakeLists.txt" <<EOF
# W861 placeholder: hipblaslt 的 clients/common 无条件 add_subdirectory 到这里，
# 但 MX 数据生成器只在 client 侧用到，我们只编 tensilelite-client，用不到。
if(NOT TARGET roc::mxdatagenerator)
  add_library(mxdatagenerator INTERFACE)
  add_library(roc::mxdatagenerator ALIAS mxdatagenerator)
endif()
EOF
ls -la "$D"

cd /out/build
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/out/deps/msgpack-cxx-6.1.1" \
  -DCMAKE_CXX_FLAGS="-I$MP -I/src/projects/hipblaslt/clients/common/include -I/src/projects/hipblaslt/library/include -DMSGPACK_ENDIAN_LITTLE_BYTE=1 -DMSGPACK_NO_BOOST=1" \
  -DCMAKE_HIP_FLAGS=-I$MP \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=ON -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=OFF \
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -DHIPBLASLT_ENABLE_MXDATAGENERATOR=OFF \
  -DHIPBLASLT_ENABLE_LAZY_LOAD=ON \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include > /out/cfg_client2.log 2>&1
echo "cfg rc=$?"; grep -cE "^CMake Error" /out/cfg_client2.log
grep -A4 "CMake Error" /out/cfg_client2.log | head -10
echo "--- build ---"
nice -n 19 timeout 1800 ninja tensilelite-client -j 12 2>&1 | tail -12
echo "--- 产物 ---"
find /out -name "tensilelite-client" -type f 2>/dev/null | head -3
'
echo "=== client2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== client2 start/,\$p" "$LOG" | tail -25
