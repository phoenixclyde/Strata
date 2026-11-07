#!/bin/bash
# W862: build + run the group/streams bench against the production kernel archive.
# Two steps: compile the bench to an object, then link with -l (a bare .a confuses the HIP driver).
set -u
R=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
O=/home/albus/w862_group
mkdir -p "$O" || exit 1
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
echo "=== build ==="
hipcc --offload-arch=gfx906 -O3 -std=c++17 \
  -I"$R/include" -I"$R/src" -I"$R/include/strata/hip_compat" \
  -c /home/albus/w862_q8_group_bench.cpp -o "$O/bench.o" > "$O/cc.log" 2>&1
if [ ! -f "$O/bench.o" ]; then echo "COMPILE FAILED"; grep -E "error:" "$O/cc.log" | head -10; exit 1; fi
hipcc --offload-arch=gfx906 "$O/bench.o" -L"$B" -lstrata_kernels -lamdhip64 -o "$O/q8_group_bench" >> "$O/cc.log" 2>&1
if [ ! -x "$O/q8_group_bench" ]; then echo "LINK FAILED"; grep -E "error|undefined" "$O/cc.log" | head -12; exit 1; fi
ls -la "$O/q8_group_bench"

for C in 1 6; do
  echo
  echo "############ ncols=$C ############"
  "$O/q8_group_bench" --iters 40 --bw 711 --cols $C --group single | grep -E 'MB|sum of isolated'
  "$O/q8_group_bench" --iters 40 --bw 711 --cols $C --group all
  "$O/q8_group_bench" --iters 40 --bw 711 --cols $C --group same
done
