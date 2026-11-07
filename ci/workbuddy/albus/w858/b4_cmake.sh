#!/bin/bash
# W858-B 续 3：手工驱动 cmake（pip 把 cmake 报错吃掉了），完整日志留证。
#   nanobind_DIR=/out/pylib/nanobind/cmake（scikit-build-core 平时就是这么注入的）
#   兄弟目录：/tmp/tree/shared/{origami,stinkytofu}
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b4.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B4 start $(date +%F" "%T)"
  docker run --rm --name strata-w858b4 -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
rm -rf /tmp/tree; mkdir -p /tmp/tree/projects/hipblaslt/tensilelite /tmp/tree/shared
cp -r /src/projects/hipblaslt/tensilelite/rocisa /tmp/tree/projects/hipblaslt/tensilelite/rocisa
cp -r /src/shared/origami /tmp/tree/shared/origami
cp -r /src/shared/stinkytofu /tmp/tree/shared/stinkytofu
R=/tmp/tree/projects/hipblaslt/tensilelite/rocisa
cmake -S $R -B /tmp/tree/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/out/rocisa-install \
  -Dnanobind_DIR=/out/pylib/nanobind/cmake \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/opt/rocm/hip;/opt/rocm/llvm" \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DHIPBLASLT_ENABLE_YAML=ON -DGPU_TARGETS=gfx906 2>&1 | tail -40
rc=${PIPESTATUS[0]}
echo "--- configure rc=$rc"
[ $rc -ne 0 ] && exit $rc
echo "--- build"
timeout 1500 nice -n 10 ninja -C /tmp/tree/build 2>&1 | tail -25
rc=${PIPESTATUS[0]}
echo "--- build rc=$rc"
[ $rc -ne 0 ] && exit $rc
rm -rf /out/rocisa-install
ninja -C /tmp/tree/build install 2>&1 | tail -6
echo "--- install 结果"
find /out/rocisa-install -name "*.so" -o -name "rocisa" -type d | head -6
PYTHONPATH=/out/rocisa-install:/out/pylib python3 -c "import rocisa,rocisa._rocisa as m;print(\"rocisa ok\");print(\"VCndMaskB16\",hasattr(m.instruction,\"VCndMaskB16\"));print(\"SAtomicCmpswapX2\",hasattr(m.instruction,\"SAtomicCmpswapX2\"))" 2>&1 | tail -4
'
  echo "=== B4 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/=== B4 start/,\$p" "$LOG" | tail -35
