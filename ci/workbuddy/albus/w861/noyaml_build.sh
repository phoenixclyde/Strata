#!/bin/bash
# W861-S: HIPBLASLT_ENABLE_YAML=OFF（纯 msgpack）—— 去掉静态链进来的 LLVM，
# 避免 llvm::cl::ParseCommandLineOptions 顶掉 comgr 自己那份 clang。
set -u
R=/home/albus/strata166
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_noyaml_build.log
: > "$LOG"
{
echo "=== noyaml build start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$OUTD":/out \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include
cd /out/build
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH=/opt/rocm \
  -DCMAKE_CXX_FLAGS="-I$MP -DMSGPACK_ENDIAN_LITTLE_BYTE=1 -DMSGPACK_NO_BOOST=1" \
  -DCMAKE_HIP_FLAGS=-I$MP \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=OFF -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=OFF \
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -Dhipblaslt_ENABLE_MXDATAGENERATOR=OFF \
  -DHIPBLASLT_ENABLE_LAZY_LOAD=ON \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include > /out/cfg_noyaml.log 2>&1
echo "cfg rc=$?"; grep -icE "^CMake Error" /out/cfg_noyaml.log
grep -iE "ENABLE_YAML|LAZY_LOAD" /out/build/CMakeCache.txt | head -3
echo "--- build ---"
nice -n 19 timeout 1800 ninja hipblaslt -j 12 2>&1 | tail -8
L=/out/build/library/libhipblaslt.so.1.4
ls -la $L 2>/dev/null
echo "--- 是否还静态链着 LLVM ---"
nm -D $L 2>/dev/null | grep -c "ParseCommandLineOptions"
'
echo "=== noyaml build end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== noyaml build start/,\$p" "$LOG" | tail -22
