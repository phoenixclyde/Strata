#!/bin/bash
# W861-J: 关掉 HIPBLASLT_ENABLE_LAZY_LOAD 重编主机库，配合 gen16 的非 lazy 库
set -u
R=/home/albus/strata166
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_nolazy_build.log
: > "$LOG"
{
echo "=== nolazy build start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=12 -v "$R/rocm-libs":/src -v "$OUTD":/out \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include
cd /out/build
echo "--- reconfigure: LAZY_LOAD=OFF ---"
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH=/opt/rocm -DCMAKE_CXX_FLAGS="-I$MP -DMSGPACK_ENDIAN_LITTLE_BYTE=1 -DMSGPACK_NO_BOOST=1" -DCMAKE_HIP_FLAGS=-I$MP \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=OFF -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=ON \
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -Dhipblaslt_ENABLE_MXDATAGENERATOR=OFF \
  -DHIPBLASLT_ENABLE_LAZY_LOAD=OFF \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include > /out/cfg_nolazy.log 2>&1
echo "cfg rc=$?"
grep -iE "^CMake Error" /out/cfg_nolazy.log | head -3
grep -i "LAZY_LOAD" /out/build/CMakeCache.txt | head -2
echo "--- rebuild library target ---"
nice -n 19 timeout 1800 ninja hipblaslt -j 12 2>&1 | tail -12
echo "--- artifacts ---"
ls -la /out/build/library/libhipblaslt.so* 2>/dev/null
'
echo "=== nolazy build end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== nolazy build start/,\$p" "$LOG" | tail -30
