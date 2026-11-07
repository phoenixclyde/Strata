#!/bin/bash
# W858-B 续：把 rocisa 跑通（带 stinkytofu / origami 兄弟目录）→ 跑 gfx906 codegen。
# 关键：rocisa 的 CMake 用相对路径找兄弟（../../../../shared/{origami,stinkytofu}），
#       所以不能只 copy rocisa，要复制成同样的层级 /tmp/tree/projects/hipblaslt/tensilelite/rocisa + /tmp/tree/shared/*。
# 内层一律双引号（单引号会截断外层 bash -lc '...'）。
set -u
SRC=/home/albus/strata166/rocm-libs
OUT=/home/albus/strata166/data/w858_hblt
LOG=/home/albus/strata166/data/w858_hblt_b2.log
IMG=strata-gfx906:0.2.9-101
mkdir -p "$OUT"; : > "$LOG"
{
  echo "=== B2 start $(date +%F" "%T)"
  docker run --rm --name strata-w858b2 -v "$SRC":/src:ro -v "$OUT":/out "$IMG" bash -lc '
set -u
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
export CMAKE_PREFIX_PATH=/opt/rocm:/opt/rocm/hip:/opt/rocm/llvm
echo "--- 搭同层级源码树"
rm -rf /tmp/tree; mkdir -p /tmp/tree/projects/hipblaslt/tensilelite /tmp/tree/shared
cp -r /src/projects/hipblaslt/tensilelite/rocisa /tmp/tree/projects/hipblaslt/tensilelite/rocisa
cp -r /src/shared/origami /tmp/tree/shared/origami
cp -r /src/shared/stinkytofu /tmp/tree/shared/stinkytofu
ls /tmp/tree/shared
echo "--- 直接 cmake 一次，先把配置错误暴露出来"
cmake -S /tmp/tree/projects/hipblaslt/tensilelite/rocisa -B /tmp/tree/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++ \
  -DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DHIPBLASLT_ENABLE_YAML=ON -DGPU_TARGETS=gfx906 2>&1 | tail -25
echo "--- configure rc=$?"
'
  echo "=== B2 end $(date +%F" "%T) rc=$?"
} >> "$LOG" 2>&1
sed -n '/--- 搭同层级/,$p' "$LOG" | tail -30
