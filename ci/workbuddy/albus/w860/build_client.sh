#!/bin/bash
# W860-B6: 重配开 TENSILELITE_ENABLE_CLIENT，编出 tensilelite-client（benchmark 必需）
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w860_client_build.log
: > "$LOG"
echo "=== build_client start ==="
docker run --rm --cpus=4 -v "$SRC":/src -v "$OUT":/out strata-gfx906:0.2.9-101 bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
MP=/out/deps/msgpack-cxx-6.1.1/include
cmake -S /src/projects/hipblaslt -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH=/opt/rocm -DCMAKE_CXX_FLAGS=-I$MP -DCMAKE_HIP_FLAGS=-I$MP \
  -DGPU_TARGETS=gfx906 -DTensile_SKIP_BUILD=ON -DTENSILELITE_ENABLE_HOST=ON \
  -DTENSILELITE_ENABLE_CLIENT=ON -DTENSILELITE_BUILD_SHARED_LIBS=OFF \
  -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=ON \
  -DHIPBLASLT_ENABLE_EXTOPS=OFF -DHIPBLASLT_ENABLE_ROCROLLER=OFF \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include > /out/cfg_client.log 2>&1
echo "cfg rc=$?"
grep -iE "^CMake Error|TENSILELITE_ENABLE_CLIENT" /out/cfg_client.log | head -5
cd /out/build
nice -n 19 timeout 1500 ninja -j 4 tensilelite-client 2>&1 | tail -12
echo "--- 产物 ---"
find /out/build -name "tensilelite-client*" -type f 2>/dev/null | head -5
' 2>&1 | tee -a "$LOG"
echo "=== build_client end ==="
tail -14 "$LOG"
