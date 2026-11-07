#!/bin/bash
# W861-S2: 给 msgpack-cxx 造一个最小 CMake config（容器里只有头文件），再关 YAML 重编
set -u
R=/home/albus/strata166
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_noyaml_build2.log
: > "$LOG"
{
echo "=== noyaml build2 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$OUTD":/out \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1
INC=$MP/include
CM=$MP/lib/cmake/msgpackc-cxx
mkdir -p "$CM"
cat > "$CM/msgpackc-cxx-config.cmake" <<EOF
# W861: 最小 config，只提供头文件路径（容器里没有 msgpack 的 dev package）
if(NOT TARGET msgpackc-cxx)
  add_library(msgpackc-cxx INTERFACE IMPORTED)
  set_target_properties(msgpackc-cxx PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "$INC")
endif()
set(msgpackc-cxx_FOUND TRUE)
EOF
cat > "$CM/msgpackc-cxx-config-version.cmake" <<EOF
set(PACKAGE_VERSION "6.1.1")
set(PACKAGE_VERSION_COMPATIBLE TRUE)
set(PACKAGE_VERSION_EXACT FALSE)
EOF
echo "--- config written ---"; ls "$CM"
cd /out/build
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH="/opt/rocm;$MP" \
  -DCMAKE_CXX_FLAGS="-I$INC -DMSGPACK_ENDIAN_LITTLE_BYTE=1 -DMSGPACK_NO_BOOST=1" \
  -DCMAKE_HIP_FLAGS=-I$INC \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=OFF -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=OFF \
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -Dhipblaslt_ENABLE_MXDATAGENERATOR=OFF \
  -DHIPBLASLT_ENABLE_LAZY_LOAD=OFF \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include > /out/cfg_noyaml2.log 2>&1
echo "cfg rc=$?"; grep -cE "^CMake Error" /out/cfg_noyaml2.log
grep -A3 "CMake Error" /out/cfg_noyaml2.log | head -6
echo "--- build ---"
nice -n 19 timeout 1800 ninja hipblaslt -j 12 2>&1 | tail -8
L=/out/build/library/libhipblaslt.so.1.4
ls -la $L 2>/dev/null
echo -n "ParseCommandLineOptions in .so: "; nm -D $L 2>/dev/null | grep -c ParseCommandLineOptions
echo -n "MessagePack defined: "; nm -D --defined-only $L 2>/dev/null | grep -c MessagePack
'
echo "=== noyaml build2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== noyaml build2 start/,\$p" "$LOG" | tail -25
