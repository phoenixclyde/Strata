#!/bin/bash
# W861-AD: strace 看它到底打开哪个库文件
set -u
R=/home/albus/strata166
LOG=$R/data/w861_strace.log
: > "$LOG"
{
echo "=== strace start $(date -u +%FT%TZ) ==="
docker run --rm --device /dev/kfd --device /dev/dri --group-add video \
  -v "$R/data/w861_lib906d":/v20/lib906:ro -v "$R/data/w859_hblt/build/library":/lt:ro \
  -v /home/albus/w861_probe4.cpp:/p4.cpp:ro strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/opt/rocm/lib
hipcc -O2 -std=c++17 /p4.cpp -o /tmp/p4 -lhipblaslt 2>/dev/null
export LD_LIBRARY_PATH=/lt:/opt/rocm/lib
if [ ! -x /usr/bin/strace ]; then echo "NO_STRACE"; ls /usr/bin | grep -i trace | head -3; exit 0; fi
strace -f -e trace=openat -o /tmp/st.txt timeout 120 /tmp/p4 /v20/lib906 256 5120 2560 >/dev/null 2>&1
echo "--- opened TensileLibrary / Mapping / hsaco ---"
grep -iE "TensileLibrary|Mapping|hsaco" /tmp/st.txt | grep -v ENOENT | head -12
echo "--- ENOENT 的尝试路径 ---"
grep -iE "TensileLibrary" /tmp/st.txt | grep ENOENT | head -8
echo "--- libhipblaslt ---"
grep -i "libhipblaslt" /tmp/st.txt | head -4
' 2>&1
echo "=== strace end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== strace start/,\$p" "$LOG" | tail -35
