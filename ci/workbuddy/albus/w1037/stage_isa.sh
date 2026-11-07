#!/bin/bash
# W1037: compile mmq.cu to gfx906 ISA twice (plain / Q4_K load-staging) and compare the instruction mix.
# No GPU is touched: --cuda-device-only -S stops at assembly.
set -u
R=/home/albus/strata166/tmp/w1037
G=$R/llama-stage
IMG=strata-gfx906:0.2.11-101
CLANG=/opt/rocm/llvm/bin/clang++

if [ ! -d "$G" ]; then
  cp -a /home/albus/strata166/llama.cpp "$G" || { echo "FAIL copy"; exit 1; }
fi
md5sum "$G/ggml/src/ggml-cuda/mmq-load-tiles.cuh"

build() {   # $1 = tag
  docker run --rm -v "$G":/g -w /g "$IMG" sh -c \
   "$CLANG -x hip --offload-arch=gfx906 --cuda-device-only -O3 -std=c++17 -DGGML_USE_HIP \
      -I/g/ggml/include -I/g/ggml/src -I/g/ggml/src/ggml-cuda \
      -S /g/ggml/src/ggml-cuda/mmq.cu -o /g/mmq_$1.s" 2> "$R/cc_$1.err"
  echo "rc=$? tag=$1 err_lines=$(wc -l < "$R/cc_$1.err")"
  [ -f "$G/mmq_$1.s" ] && echo "  lines=$(wc -l < "$G/mmq_$1.s") global_load=$(grep -c global_load "$G/mmq_$1.s") ds_write=$(grep -c ds_write "$G/mmq_$1.s") waitcnt=$(grep -c s_waitcnt "$G/mmq_$1.s") dot4=$(grep -c v_dot4_i32_i8 "$G/mmq_$1.s")"
}

echo "=== base ==="
build base
echo "=== patch ==="
python3 "$R/mmq_stage_patch.py" "$G" || { echo "FAIL patch"; exit 1; }
echo "=== staged ==="
build staged
