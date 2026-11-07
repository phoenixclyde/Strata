#!/bin/bash
# W1046: functional and ISA checks for hc4. No production process/container is touched.
set -u
S=/home/albus/strata166
W=$S/tmp/w1046
IMG=strata-gfx906:0.2.11-101
mkdir -p "$W/isa"

run_bench() {
  local tag=$1 val=$2
  echo "=== fused_gr_bench $tag (STRATA_HC_DOWN_DP4A=$val) ==="
  docker run --rm --device=/dev/kfd --device=/dev/dri \
    -e STRATA_HC_DOWN_DP4A=$val -e STRATA_TSUM=0 \
    -v $S/build-masterp:/out -v $W:/w "$IMG" \
    bash -lc 'timeout 300 /out/fused_gr_bench 24 1 8 0' 2>&1 | tee "$W/bench_$tag.log" | tail -32
}
run_bench off 0
run_bench on 1

echo "=== ISA: copy first, explicit output, never modify the build object ==="
cp "$S/build-masterp/CMakeFiles/strata_kernels.dir/src/kernels/cuda/fused_gr.cu.o" "$W/isa/fused_gr_input.o"
docker run --rm -v $W:/w "$IMG" bash -lc '
set -e
LLVM=/opt/rocm/lib/llvm/bin
$LLVM/llvm-objcopy --dump-section .hip_fatbin=/w/isa/fused_gr.fatbin /w/isa/fused_gr_input.o
T=$($LLVM/clang-offload-bundler -list -type=o -input=/w/isa/fused_gr.fatbin | grep gfx906 | head -1)
echo "target=$T"
$LLVM/clang-offload-bundler -type=o -unbundle -targets=$T -input=/w/isa/fused_gr.fatbin -output=/w/isa/fused_gr_code.o
$LLVM/llvm-objdump -d --mcpu=gfx906 /w/isa/fused_gr_code.o > /w/isa/fused_gr.s
echo "lines=$(wc -l < /w/isa/fused_gr.s)"
echo "dot4=$(grep -c v_dot4_i32_i8 /w/isa/fused_gr.s)"
echo "dot8=$(grep -c v_dot8_i32_i4 /w/isa/fused_gr.s)"
echo "mad_i24=$(grep -c v_mad_i32_i24 /w/isa/fused_gr.s)"
grep -n "gr_down_q8_dp4a_kernel" /w/isa/fused_gr.s | head -4
'
md5sum "$S/build-masterp/CMakeFiles/strata_kernels.dir/src/kernels/cuda/fused_gr.cu.o" "$W/isa/fused_gr_input.o"
echo "VERIFY_B3: DONE"
