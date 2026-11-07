#!/bin/bash
# W858 B1+B2：造配对 rocisa（CPU 交叉编译，不需 GPU）→ 用它跑 gfx906 codegen。
# 墙（W856）：镜像只装 _rocisa.abi3.so，没有 Python 包；源码 Python 与 .so 指令集不配对。
# 注意：docker run 的内层一律用双引号——单引号会截断外层 bash -lc '...'（W858 踩过）。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b1.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B start $(date +%F" "%T)"
  docker run --rm --name strata-w858hblt -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export CMAKE_PREFIX_PATH=/opt/rocm:/opt/rocm/hip
echo "--- backend"
PIPARGS="--no-cache-dir --timeout 90 --retries 6 -i https://pypi.tuna.tsinghua.edu.cn/simple"
if ! PYTHONPATH=/out/pylib python3 -c "import scikit_build_core,nanobind" 2>/dev/null; then
  python3 -m pip install $PIPARGS --target /out/pylib "scikit-build-core>=0.10" "nanobind>=2.0,!=3.0.0" 2>&1 | tail -3
fi
if ! PYTHONPATH=/out/pylib python3 -c "import scikit_build_core,nanobind" 2>/dev/null; then
  echo "--- 清华源不可用，改阿里云"
  python3 -m pip install --no-cache-dir --timeout 90 --retries 6 -i https://mirrors.aliyun.com/pypi/simple --target /out/pylib "scikit-build-core>=0.10" "nanobind>=2.0,!=3.0.0" 2>&1 | tail -3
fi
PYTHONPATH=/out/pylib python3 -c "import scikit_build_core,nanobind;print(\"backend ok\",scikit_build_core.__version__)" 2>&1 | tail -1

echo "--- build rocisa from source"
rm -rf /tmp/rsrc && cp -r /src/projects/hipblaslt/tensilelite/rocisa /tmp/rsrc
cd /tmp/rsrc
rm -rf /out/pylib2
PYTHONPATH=/out/pylib python3 -m pip install --no-build-isolation --no-cache-dir --timeout 90 --target /out/pylib2 . 2>&1 | tail -14
echo "--- import + 指令集"
PYTHONPATH=/out/pylib2 python3 -c "import rocisa,rocisa._rocisa as m;print(\"rocisa\",rocisa.__file__);print(\"VCndMaskB16\",hasattr(m.instruction,\"VCndMaskB16\"));print(\"SAtomicCmpswapX2\",hasattr(m.instruction,\"SAtomicCmpswapX2\"))" 2>&1 | tail -4

echo "--- B2 gfx906 codegen"
TL=/src/projects/hipblaslt/tensilelite
Y=$TL/Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml
ls -l $Y 2>&1 | head -1
rm -rf /out/gen; mkdir -p /out/gen
cd $TL
PYTHONPATH=/out/pylib2:$TL timeout 900 python3 Tensile/bin/TensileCreateLibrary \
  --architecture=gfx906 --logic=$Y --output-path=/out/gen \
  --code-object-version=5 --library-format=yaml 2>&1 | tail -22
echo "--- 产物"
find /out/gen -type f | head -12
echo "--- hsaco 里的 arch"
for f in $(find /out/gen -name "*.hsaco" | head -2); do echo $f; strings $f | grep -m2 -E "gfx9|amdhsa" ; done
'
  echo "=== B end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n '/--- backend/,$p' "$LOG" | tail -40
