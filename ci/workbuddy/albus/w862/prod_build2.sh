#!/bin/bash
# W862: rebuild the patched kernel with the EXACT flags CMake used (read out of build.ninja),
# so the numbers are comparable with the production archive.  /src in the ninja file is this tree.
set -u
R=/home/albus/strata166/pr/strata-fork
O=/home/albus/w862_prod
B=/home/albus/strata166/gfx029-build
export PATH=/opt/rocm/bin:/opt/rocm/llvm/bin:$PATH
DEF='-DSTRATA_HAVE_DFLASH2=1 -DSTRATA_HIP_GFX906=1 -DSTRATA_VERIFY_MAX_T=8 -DSTRATA_VERSION="0.1.55" -DUSE_PROF_API=1 -D__HIP_PLATFORM_AMD__=1 -D__HIP_ROCclr__=1'
INC="-I$R/third_party/ggml -I$R/include -isystem $R/include/strata/platform/hip_compat -isystem /opt/rocm/include"
FLAGS="-O3 -DNDEBUG -std=c++20 --offload-arch=gfx906 -Wall -Wextra"
mkdir -p "$O" || exit 1

echo "=== compile patched kernel (exact CMake flags) ==="
if [ ! -f "$O/nm862b.o" ]; then
  eval hipcc $FLAGS $DEF $INC -c "$R/src/kernels/cuda/native_mmvq.cu" -o "$O/nm862b.o" > "$O/nm_cc2.log" 2>&1
  if [ ! -f "$O/nm862b.o" ]; then echo "KERNEL COMPILE FAILED"; grep -E "error:" "$O/nm_cc2.log" | head -8; exit 1; fi
fi
ls -la "$O/nm862b.o"

echo "=== compile bench (same includes) ==="
eval hipcc $FLAGS $DEF $INC -c /home/albus/w862_q8_group_bench.cpp -o "$O/bench2.o" > "$O/bench_cc2.log" 2>&1
if [ ! -f "$O/bench2.o" ]; then echo "BENCH COMPILE FAILED"; grep -E "error:" "$O/bench_cc2.log" | head -8; exit 1; fi
hipcc --offload-arch=gfx906 "$O/bench2.o" "$O/nm862b.o" -L"$B" -lstrata_kernels -lamdhip64 \
  -Wl,-z,muldefs -o "$O/q8_prod_bench2" >> "$O/bench_cc2.log" 2>&1
if [ ! -x "$O/q8_prod_bench2" ]; then echo "LINK FAILED"; grep -E "undefined|error" "$O/bench_cc2.log" | head -8; exit 1; fi
echo built

echo "=== A/B: R=1 vs table, real kernel, production flags ==="
for C in 1 6; do
  for RW in 1 0; do
    echo "-- ncols=$C  $([ $RW -eq 0 ] && echo 'R=table' || echo 'R=1') --"
    "$O/q8_prod_bench2" --iters 40 --bw 711 --cols $C --rows $RW --group all | grep -E 'serial'
    "$O/q8_prod_bench2" --iters 40 --bw 711 --cols $C --rows $RW --group single | grep -E 'MB|sum of isolated'
  done
done
echo "=== parity (production flags) ==="
"$O/q8_prod_bench2" --cols 6 --rows 0 --group check | tail -11
"$O/q8_prod_bench2" --cols 1 --rows 0 --group check | tail -11
