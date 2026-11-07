#!/bin/bash
# W861-N: 定位 comgr 在哪一步失败（verbose logs）+ 试关闭 JIT 相关的环境变量
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906b
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_probe4b.log
: > "$LOG"
{
echo "=== probe4b start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
hipcc -O2 -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
echo "===== A) 带 comgr verbose ====="
AMD_COMGR_EMIT_VERBOSE_LOGS=1 AMD_COMGR_REDIRECT_LOGS=stderr ROCBLASLT_LOG_LEVEL=2 \
  timeout 120 /tmp/probe4 - 64 64 64 2>&1 | head -40
echo "rc=$?"
echo
echo "===== B) 不设库路径（用系统库，看基线行为） ====="
unset HIPBLASLT_TENSILE_LIBPATH
timeout 120 /tmp/probe4 - 64 64 64 2>&1 | head -12
echo "rc=$?"
' 2>&1
echo "=== probe4b end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== probe4b start/,\$p" "$LOG" | tail -60
