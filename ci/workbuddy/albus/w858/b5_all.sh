#!/bin/bash
# W858-B 续 4：配置已过 → 编译 / 安装 / 导入检查 / gfx906 codegen，一条龙（/tmp 不跨容器）。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b5.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B5 start $(date +%F" "%T)"
  docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
    -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
    -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
rm -rf /tmp/tree; mkdir -p /tmp/tree/projects/hipblaslt/tensilelite /tmp/tree/shared
cp -r /src/projects/hipblaslt/tensilelite/rocisa /tmp/tree/projects/hipblaslt/tensilelite/rocisa
cp -r /src/shared/origami /tmp/tree/shared/origami
cp -r /src/shared/stinkytofu /tmp/tree/shared/stinkytofu
cp -r /src/cmake /tmp/tree/cmake
cmake -S /tmp/tree/projects/hipblaslt/tensilelite/rocisa -B /tmp/tree/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/out/rocisa-install \
  -Dnanobind_DIR=/out/pylib/nanobind/cmake \
  -DCMAKE_PREFIX_PATH="/opt/rocm;/opt/rocm/hip;/opt/rocm/llvm" \
  -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DHIPBLASLT_ENABLE_YAML=ON -DGPU_TARGETS=gfx906 > /out/cfg_full.log 2>&1
echo "--- configure rc=$?"
echo "--- build $(date +%H:%M:%S)"
timeout 2400 nice -n 10 ninja -C /tmp/tree/build -j 14 2>&1 | tail -18
echo "--- build done $(date +%H:%M:%S)"
[ -f /tmp/tree/build/rocisa/_rocisa*.so ] || ls /tmp/tree/build | head
rm -rf /out/rocisa-install
ninja -C /tmp/tree/build install 2>&1 | tail -4
echo "--- install"
find /out/rocisa-install -name "*.so" | head -3
PYTHONPATH=/out/rocisa-install:/out/pylib python3 -c "import rocisa;print(\"rocisa\",rocisa.__file__);import rocisa._rocisa as m;print(\"VCndMaskB16\",hasattr(m.instruction,\"VCndMaskB16\"));print(\"SAtomicCmpswapX2\",hasattr(m.instruction,\"SAtomicCmpswapX2\"))" 2>&1 | tail -4

echo "--- gfx906 codegen $(date +%H:%M:%S)"
TL=/src/projects/hipblaslt/tensilelite
Y=$TL/Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml
rm -rf /out/gen; mkdir -p /out/gen
cd $TL
PYTHONPATH=/out/rocisa-install:/out/pylib:$TL timeout 1200 python3 Tensile/bin/TensileCreateLibrary \
  --architecture=gfx906 --logic=$Y --output-path=/out/gen \
  --code-object-version=5 --library-format=yaml 2>&1 | tail -25
echo "--- 产物"
find /out/gen -type f | head -12
for f in $(find /out/gen -name "*.hsaco" -o -name "*.co" | head -2); do echo "== $f"; strings $f | grep -m3 -E "gfx906|amdhsa" ; done
'
  echo "=== B5 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
grep -E "configure rc|build done|install|rocisa |VCndMask|SAtomic|codegen|产物|gfx906|B5 end" "$LOG" | tail -20
