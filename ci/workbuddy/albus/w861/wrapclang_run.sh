#!/bin/bash
# W861-Q: 用 clang wrapper 过滤 comgr 传的废弃参数，看 hipblasLtCreate 是否过关
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906y
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_wrapclang.log
: > "$LOG"
{
echo "=== wrapclang start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro -v /home/albus/w861_wrap_clang.sh:/wrapwrap.sh:ro \
  -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
# 装 wrapper：PATH 最前面放一个叫 clang 的脚本
mkdir -p /tmp/wrap
cp /wrapwrap.sh /tmp/wrap/clang && chmod 755 /tmp/wrap/clang
rm -f /tmp/wrap_clang.log
export PATH=/tmp/wrap:$PATH
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
echo "--- which clang ---"; which clang
echo "--- probe3 (create only, 显式 libpath) ---"
cd /probe && timeout 120 ./probe3 /v20/lib906 2>&1 | grep -viE "LLVM option|Did you mean" | head -10
echo "--- wrapper 被调用次数 ---"; wc -l /tmp/wrap_clang.log 2>/dev/null || echo 0
head -2 /tmp/wrap_clang.log 2>/dev/null | cut -c1-200
echo "--- probe4 小形状 ---"
timeout 120 /tmp/probe4 - 64 64 64 2>&1 | grep -viE "LLVM option|Did you mean"
' 2>&1
echo "=== wrapclang end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== wrapclang start/,\$p" "$LOG" | tail -40
