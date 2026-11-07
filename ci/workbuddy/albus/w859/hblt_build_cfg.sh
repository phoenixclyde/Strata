#!/bin/bash
# W859-B：自己编 hipBLASLt 主机库（gfx906）
#   依据：① 发行版里 libhipblaslt 在 gfx906 上是"dummy placeholder"（Gentoo 960513）
#         ② 官方文档：-DTensile_SKIP_BUILD=ON 只编主机库，device 库用 HIPBLASLT_TENSILE_LIBPATH 外挂
#   前置：roc-libs 已 sparse add projects/hipblaslt|shared/{origami,stinkytofu}|cmake，且 /out/rocisa-install 可用
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w859_hblt
LOG=/home/albus/strata166/data/w859_hblt_build.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B-build start $(date +%F" "%T)"
  docker run --rm --name strata-w859hblt -v "$SRC":/src -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
H=/src/projects/hipblaslt
echo "--- 打开 gfx906 白名单"
F1=$H/cmake/tensilelite_supported_architectures.cmake
F2=$H/tensilelite/cmake/tensilelite_supported_architectures.cmake
for f in $F1 $F2; do
  [ -f "$f" ] || continue
  echo "  patching $f"
  python3 - "$f" <<PYX
import io, sys
p = sys.argv[1]
s = io.open(p, encoding="utf-8").read()
if "\"gfx906\"" not in s:
    s = s.replace("set(SUPPORTED_ARCHITECTURES\n", "set(SUPPORTED_ARCHITECTURES\n    \"gfx906\"\n", 1)
    s = s.replace("set(SUPPORTED_ARCHITECTURES_LEGACY\n", "set(SUPPORTED_ARCHITECTURES_LEGACY\n    \"gfx906\"\n", 1)
    io.open(p, "w", encoding="utf-8").write(s)
print("  gfx906 in file:", "\"gfx906\"" in io.open(p, encoding="utf-8").read())
PYX
done

echo "--- configure（主机库，不编 Tensile device 库）"
rm -rf /out/build
cmake -S $H -B /out/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_HIP_ARCHITECTURES=gfx906 \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/opt/rocm/hip;/opt/rocm/llvm" \
  -DGPU_TARGETS=gfx906 \
  -DTensile_SKIP_BUILD=ON -DHIPBLASLT_ENABLE_CLIENT=OFF -DHIPBLASLT_ENABLE_YAML=ON \
  -DBUILD_CLIENTS_SAMPLES=OFF -DBUILD_CLIENTS_TESTS=OFF -DBUILD_CLIENTS_BENCHMARKS=OFF \
  -DHIPBLASLT_ENABLE_ROCROLLER=OFF -DHIPBLASLT_ENABLE_ASAN=OFF \
  -Dzstd_LIBRARY=/usr/lib/x86_64-linux-gnu/libzstd.so.1 \
  -Dzstd_INCLUDE_DIR=/opt/rocm/lib/rocm_sysdeps/include \
  > /out/cfg.log 2>&1
echo "--- configure rc=$?"
grep -i -m8 -E "CMake Error|Could NOT find|not found" /out/cfg.log | head -10
tail -3 /out/cfg.log
'
  echo "=== B-build end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== B-build start/,\$p" "$LOG" | tail -30
