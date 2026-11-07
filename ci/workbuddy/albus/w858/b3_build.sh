#!/bin/bash
# W858-B 续 2：用 pip（scikit-build-core）编 rocisa —— 它会自己把 nanobind 注入 CMAKE_PREFIX_PATH。
#   前提：/tmp/tree 下按原层级放好 rocisa + shared/{origami,stinkytofu}；/out/pylib 已有 scikit-build-core+nanobind+joblib。
#   然后跑 gfx906 codegen，最后拿产物判"生成器到底能不能出 vega20 的机器码"。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b3.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B3 start $(date +%F" "%T)"
  docker run --rm --name strata-w858b3 -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export CMAKE_PREFIX_PATH=/opt/rocm:/opt/rocm/hip:/opt/rocm/llvm
echo "--- 依赖（幂等）"
PIP="python3 -m pip install --no-cache-dir --timeout 90 --retries 6 -i https://mirrors.aliyun.com/pypi/simple"
if ! PYTHONPATH=/out/pylib python3 -c "import scikit_build_core,nanobind,joblib" 2>/dev/null; then
  $PIP --target /out/pylib "scikit-build-core>=0.10" "nanobind>=2.0,!=3.0.0" joblib 2>&1 | tail -3
fi
PYTHONPATH=/out/pylib python3 -c "import scikit_build_core,nanobind,joblib;print(\"deps ok\")" 2>&1 | tail -1

echo "--- 源码树（同层级）"
rm -rf /tmp/tree; mkdir -p /tmp/tree/projects/hipblaslt/tensilelite /tmp/tree/shared
cp -r /src/projects/hipblaslt/tensilelite/rocisa /tmp/tree/projects/hipblaslt/tensilelite/rocisa
cp -r /src/shared/origami /tmp/tree/shared/origami
cp -r /src/shared/stinkytofu /tmp/tree/shared/stinkytofu

echo "--- pip 编 rocisa（含 stinkytofu，MLIR 可能要几分钟）"
cd /tmp/tree/projects/hipblaslt/tensilelite/rocisa
rm -rf /out/pylib2
PYTHONPATH=/out/pylib timeout 1500 python3 -m pip install --no-build-isolation --no-cache-dir \
  --target /out/pylib2 . 2>&1 | tail -25
echo "--- 导入检查"
PYTHONPATH=/out/pylib2 python3 -c "import rocisa,rocisa._rocisa as m;print(\"rocisa\",rocisa.__file__);print(\"VCndMaskB16\",hasattr(m.instruction,\"VCndMaskB16\"));print(\"SAtomicCmpswapX2\",hasattr(m.instruction,\"SAtomicCmpswapX2\"))" 2>&1 | tail -4

echo "--- gfx906 codegen"
TL=/src/projects/hipblaslt/tensilelite
Y=$TL/Tensile/Tests/unit/characterization/_codegen/data/gfx1100/SB.yaml
ls -l $Y 2>&1 | head -1
rm -rf /out/gen; mkdir -p /out/gen
cd $TL
PYTHONPATH=/out/pylib2:/out/pylib:$TL timeout 900 python3 Tensile/bin/TensileCreateLibrary \
  --architecture=gfx906 --logic=$Y --output-path=/out/gen \
  --code-object-version=5 --library-format=yaml 2>&1 | tail -25
echo "--- 产物"
find /out/gen -type f | head -12
for f in $(find /out/gen -name "*.hsaco" -o -name "*.co" | head -2); do echo "== $f"; file $f 2>/dev/null; strings $f | grep -m2 -E "gfx9|amdhsa" ; done
'
  echo "=== B3 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n "/--- 依赖/,\$p" "$LOG" | tail -40
