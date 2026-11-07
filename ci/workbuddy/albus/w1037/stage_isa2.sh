#!/bin/bash
# W1037 v2: compile the Q4_K MMQ *instance* to gfx906 ISA twice (plain / load-staging) and compare.
# v1 compiled mmq.cu, which contains no explicit instantiations -> 29-line empty .s with rc=0 (a silent no-op).
set -u
R=/home/albus/strata166/tmp/w1037
G=$R/llama-stage
IMG=strata-gfx906:0.2.11-101
CLANG=/opt/rocm/llvm/bin/clang++
SRC=/g/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu

build() {   # $1 = tag
  docker run --rm -v "$G":/g -w /g "$IMG" sh -c \
   "$CLANG -x hip --offload-arch=gfx906 --cuda-device-only -O3 -std=c++17 -DGGML_USE_HIP \
      -I/g/ggml/include -I/g/ggml/src -I/g/ggml/src/ggml-cuda \
      -S $SRC -o /g/mmq_$1.s" 2> "$R/cc_$1.err"
  rc=$?
  echo "rc=$rc tag=$1 err_lines=$(wc -l < "$R/cc_$1.err")"
  if [ -f "$G/mmq_$1.s" ]; then
    echo "  lines=$(wc -l < "$G/mmq_$1.s") gld=$(grep -c global_load "$G/mmq_$1.s") ds_write=$(grep -c ds_write "$G/mmq_$1.s") waitcnt=$(grep -c s_waitcnt "$G/mmq_$1.s") dot4=$(grep -c v_dot4_i32_i8 "$G/mmq_$1.s") vgpr_max=$(grep -o 'vgpr_count: [0-9]*' "$G/mmq_$1.s" | sort -u | head -3 | tr '\n' ' ')"
  fi
  return $rc
}

echo "=== revert to plain, build base ==="
python3 "$R/mmq_stage_patch.py" "$G" --revert || true
md5sum "$G/ggml/src/ggml-cuda/mmq-load-tiles.cuh"
build base || { echo "FAIL base"; exit 1; }
echo "=== patch, build staged ==="
python3 "$R/mmq_stage_patch.py" "$G" || { echo "FAIL patch"; exit 1; }
md5sum "$G/ggml/src/ggml-cuda/mmq-load-tiles.cuh"
build staged || { echo "FAIL staged"; exit 1; }
