#!/bin/bash
# W862: build the patched production kernel object, then check parity and measure with it.
# Production container is untouched: this only produces an object file under /home/albus.
set -u
R=/home/albus/strata166/pr/strata-fork
O=/home/albus/w862_prod
B=/home/albus/strata166/gfx029-build
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
INC="-I$R/include -I$R/src -I$R/src/kernels/cuda -I$R/include/strata/hip_compat"
DEF="-DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -DNDEBUG"
mkdir -p "$O" || exit 1

echo "=== 1. patch (with backup) ==="
python3 /home/albus/w862_patch_wave_rows.py || exit 1

echo "=== 2. compile the patched kernel ==="
if [ ! -f "$O/nm862.o" ]; then
  hipcc --offload-arch=gfx906 -O3 -std=c++17 $DEF $INC \
    -c "$R/src/kernels/cuda/native_mmvq.cu" -o "$O/nm862.o" > "$O/nm_cc.log" 2>&1
  if [ ! -f "$O/nm862.o" ]; then echo "KERNEL COMPILE FAILED"; grep -E "error:" "$O/nm_cc.log" | head -10; exit 1; fi
fi
ls -la "$O/nm862.o"

echo "=== 3. bench against the patched kernel ==="
hipcc --offload-arch=gfx906 -O3 -std=c++17 $DEF $INC \
  -c /home/albus/w862_q8_group_bench.cpp -o "$O/bench.o" > "$O/bench_cc.log" 2>&1
hipcc --offload-arch=gfx906 "$O/bench.o" "$O/nm862.o" -L"$B" -lstrata_kernels -lamdhip64 \
  -Wl,-z,muldefs -o "$O/q8_prod_bench" >> "$O/bench_cc.log" 2>&1
if [ ! -x "$O/q8_prod_bench" ]; then echo "LINK FAILED"; grep -E "undefined|error" "$O/bench_cc.log" | head -10; exit 1; fi
echo "built"

echo "=== 4. parity: R table vs R=1, real kernel ==="
for C in 1 6; do
  echo "-- ncols=$C  table vs R=1 --"
  "$O/q8_prod_bench" --cols $C --rows 0 --group check | tail -11
done
echo "=== 5. throughput: R=1 vs table ==="
for C in 1 6; do
  for RW in 1 0; do
    echo "-- ncols=$C rows=$([ $RW -eq 0 ] && echo table || echo 1) --"
    "$O/q8_prod_bench" --iters 40 --bw 711 --cols $C --rows $RW --group all | grep -E 'serial|streams 2'
    "$O/q8_prod_bench" --iters 40 --bw 711 --cols $C --rows $RW --group single | grep -E 'MB|sum of isolated'
  done
done
