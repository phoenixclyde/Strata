#!/bin/bash
# 在容器里取 fused_gr_bench 的构建命令，并看它的 CLI
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101
echo "=== CLI / usage of the bench ==="
grep -n "argv\|usage\|--" "$S/src/kernels/fused_gr_bench.cpp" | head -20
echo
echo "=== the build commands (in container) ==="
docker run --rm --security-opt label=disable -v "$S":/src -v "$B":/out "$IMG" bash -lc '
cd /out
ninja -t commands fused_gr_bench > /out/_fgb.txt 2>&1
echo "lines: $(wc -l < /out/_fgb.txt)"
echo "--- compile line ---"
grep "fused_gr_bench.cpp.o" /out/_fgb.txt | grep -v "^.*-o CMakeFiles.*-c.*-c" | head -1 | cut -c1-300
echo "--- link line ---"
tail -1 /out/_fgb.txt | cut -c1-300
' 2>&1 | tail -12
