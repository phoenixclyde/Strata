#!/bin/bash
# W1037 v3: two trees instead of revert-in-place (the script's --revert path is broken; do not rely on it).
set -u
R=/home/albus/strata166/tmp/w1037
IMG=strata-gfx906:0.2.11-101
CLANG=/opt/rocm/llvm/bin/clang++
SRC=/g/ggml/src/ggml-cuda/template-instances/mmq-instance-q4_k.cu

build() {   # $1 = tree dir, $2 = tag, $3 = extra -D
  docker run --rm -v "$1":/g -w /g "$IMG" sh -c \
   "$CLANG $DEF -x hip --offload-arch=gfx906 --cuda-device-only -O3 -std=c++17 -DGGML_USE_HIP \
      -I/g/ggml/include -I/g/ggml/src -I/g/ggml/src/ggml-cuda \
      -S $SRC -o /g/mmq_$2.s" 2> "$R/cc_$2.err"
  rc=$?
  echo "rc=$rc tag=$2 err=$(wc -l < "$R/cc_$2.err") md5_load_tiles=$(md5sum "$1/ggml/src/ggml-cuda/mmq-load-tiles.cuh" | cut -c1-12)"
  if [ -f "$1/mmq_$2.s" ]; then
    echo "  lines=$(wc -l < "$1/mmq_$2.s") gld=$(grep -c global_load "$1/mmq_$2.s") ds_write=$(grep -c ds_write "$1/mmq_$2.s") waitcnt=$(grep -c s_waitcnt "$1/mmq_$2.s") dot4=$(grep -c v_dot4_i32_i8 "$1/mmq_$2.s")"
  fi
}

[ -d "$R/llama-plain" ] || cp -a /home/albus/strata166/llama.cpp "$R/llama-plain"
echo "=== base (pristine copy) ==="
DEF="" build "$R/llama-plain" base
echo "=== staged (patched copy) ==="
grep -c STRATA_GFX906_MMQ_STAGE "$R/llama-stage/ggml/src/ggml-cuda/mmq-load-tiles.cuh"
DEF="-DSTRATA_GFX906_MMQ_STAGE" build "$R/llama-stage" staged

echo "=== per-kernel detail: the largest kernel of each ==="
for t in base staged; do
  d=$R/llama-plain; [ "$t" = staged ] && d=$R/llama-stage
  echo "-- $t"
  grep -c "^_Z" "$d/mmq_$t.s" 2>/dev/null || true
  grep -o "vgpr_count: *[0-9]*" "$d/mmq_$t.s" | sort | uniq -c | sort -rn | head -3
  grep -o "sgpr_count: *[0-9]*" "$d/mmq_$t.s" | sort | uniq -c | sort -rn | head -3
done
