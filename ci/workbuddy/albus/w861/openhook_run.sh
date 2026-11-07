#!/bin/bash
# W861-AE: open hook -- 抓引擎实际读取的库文件
set -u
R=/home/albus/strata166
LOG=$R/data/w861_openhook.log
: > "$LOG"
{
echo "=== openhook start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$R/data/w861_lib906d":/v20/lib906:ro -v "$R/data/w859_hblt/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro -v /home/albus/w861_open_hook.c:/hook.c:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:/usr/bin:/bin
export LD_LIBRARY_PATH=/opt/rocm/lib
gcc -shared -fPIC -O1 -o /tmp/oh.so /hook.c -ldl 2>&1 | head -3
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
LD_PRELOAD=/tmp/oh.so timeout 120 /tmp/p4 /v20/lib906 256 5120 2560 2>&1 \
  | grep -viE "LLVM option|Did you mean" | head -30
' 2>&1
echo "=== openhook end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== openhook start/,\$p" "$LOG" | tail -35
