#!/bin/bash
# W861-C2: 挂上现成的 llama.cpp（src028/third_party）让 cmake 配置通过，编 fused_gr_bench
set -u
R=/home/albus/strata166
LLM=$R/src028/third_party/llama.cpp
LOG=$R/data/w861_gr_build2.log
: > "$LOG"
{
echo "=== gr build2 start $(date -u +%FT%TZ) ==="
docker run --rm --cpus=8 \
  -v "$R/gfx029":/src -v "$R/gfx029-build":/out -v "$LLM":/llama.cpp:ro \
  strata-gfx906:0.2.9-101 bash -lc '
set -u
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
export LD_LIBRARY_PATH=/opt/rocm/lib:${LD_LIBRARY_PATH:-}
echo "--- ggml present? ---"; ls /llama.cpp/ggml/include/ggml.h 2>&1
cd /out
echo "--- reconfigure via build ---"
nice -n 19 timeout 600 cmake --build . --target fused_gr_bench -j 8 2>&1 | tail -30
echo "--- binary ---"
ls -l /out/fused_gr_bench 2>/dev/null || echo MISSING
'
echo "=== gr build2 end $(date -u +%FT%TZ) ==="
} >> "$LOG" 2>&1
sed -n "/=== gr build2 start/,\$p" "$LOG" | tail -40
