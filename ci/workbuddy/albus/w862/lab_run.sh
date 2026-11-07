#!/bin/bash
# W862 lab: build a copy of native_mmvq.cu whose Q8_0 wave kernel takes rows-per-wave (R) from
# a knob, then sweep R x ncols against the production shapes.  Production tree is untouched;
# the lab .cu is a file copy in /home/albus/w862_lab.
set -u
R=/home/albus/strata166/pr/strata-fork
O=/home/albus/w862_lab
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
INC="-I$R/include -I$R/src -I$R/src/kernels/cuda -I$R/include/strata/hip_compat"
DEF="-DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -DNDEBUG"
mkdir -p "$O" || exit 1

echo "=== 1. patch a copy ==="
python3 /home/albus/w862_lab_patch.py || exit 1

echo "=== 2. compile the lab kernel object (this is the long one) ==="
if [ ! -f "$O/lab.o" ]; then
  hipcc --offload-arch=gfx906 -O3 -std=c++17 $DEF $INC -c "$O/native_mmvq_lab.cu" -o "$O/lab.o" > "$O/lab_cc.log" 2>&1
  if [ ! -f "$O/lab.o" ]; then echo "LAB COMPILE FAILED"; grep -E "error:" "$O/lab_cc.log" | head -10; exit 1; fi
fi
ls -la "$O/lab.o"

echo "=== 3. compile + link the bench against it ==="
hipcc --offload-arch=gfx906 -O3 -std=c++17 $DEF $INC -c /home/albus/w862_q8_group_bench.cpp -o "$O/bench.o" > "$O/bench_cc.log" 2>&1
if [ ! -f "$O/bench.o" ]; then echo "BENCH COMPILE FAILED"; grep -E "error:" "$O/bench_cc.log" | head -10; exit 1; fi
hipcc --offload-arch=gfx906 "$O/bench.o" "$O/lab.o" -L/home/albus/strata166/gfx029-build -lstrata_kernels -lamdhip64 -Wl,-z,muldefs -o "$O/q8_lab_bench" >> "$O/bench_cc.log" 2>&1
if [ ! -x "$O/q8_lab_bench" ]; then echo "LINK FAILED"; grep -E "undefined|error" "$O/bench_cc.log" | head -14; exit 1; fi
ls -la "$O/q8_lab_bench"

echo "=== 4. bitwise parity (rows 2 vs 1) ==="
for C in 1 6; do
  for RW in 2 4; do
    echo "-- ncols=$C rows=$RW --"
    "$O/q8_lab_bench" --cols $C --rows $RW --group check | tail -12
  done
done

echo "=== 5. sweep ==="
for C in 1 6; do
  for RW in 1 2 4; do
    echo
    echo "---- ncols=$C  rows=$RW ----"
    "$O/q8_lab_bench" --iters 30 --bw 711 --cols $C --rows $RW --group all | grep -E 'serial|streams 2|FUSED'
    "$O/q8_lab_bench" --iters 30 --bw 711 --cols $C --rows $RW --group same | grep -E 'serial|streams 3|FUSED'
  done
done
