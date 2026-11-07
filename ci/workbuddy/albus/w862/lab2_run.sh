#!/bin/bash
# W862: build + run the self-contained Q8_0 wave lab (compiles in seconds, no project headers).
set -u
O=/home/albus/w862_lab2
mkdir -p "$O" || exit 1
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
hipcc --offload-arch=gfx906 -O3 -DNDEBUG -std=c++17 \
  /home/albus/w862_q8_wave_lab.cu -o "$O/q8_wave_lab" > "$O/cc.log" 2>&1
if [ ! -x "$O/q8_wave_lab" ]; then echo "BUILD FAILED"; grep -E "error:" "$O/cc.log" | head -12; exit 1; fi
echo "built: $(ls -la "$O/q8_wave_lab" | awk '{print $5" bytes"}')"
"$O/q8_wave_lab" --iters 30 --bw 711 --check
