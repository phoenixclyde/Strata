#!/bin/bash
# W861-R: LD_PRELOAD 抓 exit 的 backtrace，定位真正的触发点
set -u
R=/home/albus/strata166
LIB=$R/data/w861_lib906y
OUTD=$R/data/w859_hblt
LOG=$R/data/w861_exithook.log
: > "$LOG"
{
echo "=== exithook start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$LIB":/v20/lib906:ro -v "$OUTD/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/probe4.cpp:ro -v /home/albus/w861_exit_hook.c:/hook.c:ro \
  -v "$R/data/w858_hblt":/probe:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
echo "--- build hook + probe (rdynamic 才有符号名) ---"
gcc -shared -fPIC -O1 -o /tmp/hook.so /hook.c -ldl 2>&1 | tail -3
hipcc -O2 -g -rdynamic -std=c++17 /probe4.cpp -o /tmp/probe4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
export HIPBLASLT_TENSILE_LIBPATH=/v20/lib906
echo "--- run with hook ---"
LD_PRELOAD=/tmp/hook.so timeout 120 /tmp/probe4 - 64 64 64 2>&1 | grep -viE "LLVM option|Did you mean" | head -45
echo "rc=$?"
' 2>&1
echo "=== exithook end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== exithook start/,\$p" "$LOG" | tail -50
