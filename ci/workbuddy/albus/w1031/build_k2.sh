#!/bin/bash
# K 系列（第二版）：overlay 关掉（避免 cmake 脚本对新头做锚点补丁），粘合层先试 src-v090（prec + 新 pool），
# 若报 new_pool_for_device 不匹配就退回 src-a3（prec + 旧 pool）。
set -u
IMG=strata-gfx906:0.2.11-101
BASE=/home/albus/strata166/ref/llama_b12110
CL=/home/albus/strata166/w1031/lcpp
FILES="mmq.cuh mmq-load-tiles.cuh mmq-vec-dot.cuh vecdotq.cuh quantize.cu quantize.cuh mma.cuh dequantize.cuh common.cuh"

mk () {
  local n=$1 sha=$2 LL=/home/albus/strata166/w1031/$1
  rm -rf "$LL"; cp -a "$BASE" "$LL"
  for f in $FILES; do
    ( cd "$CL" && git show "$sha:ggml/src/ggml-cuda/$f" ) > "$LL/ggml/src/ggml-cuda/$f" || exit 4
  done
  echo "$n ready: mmq=$(md5sum $LL/ggml/src/ggml-cuda/mmq.cuh | cut -c1-8)"
}

try_build () {  # try_build <name> <out> <src>
  local n=$1 OUT=/home/albus/strata166/$2 SRC=$3 LL=/home/albus/strata166/w1031/$1
  mkdir -p "$OUT"; cp -f /home/albus/strata166/build-v090/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
  docker rm -f "b_$n" >/dev/null 2>&1
  docker run --rm --name "b_$n" --device=/dev/kfd --device=/dev/dri \
    -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc "
cd /out; cmake -S /src -B /out -G Ninja -DSTRATA_MMQ_TQ_OVERLAY=OFF > /out/_c.log 2>&1; echo \"[$n] CMAKE_RC=\$?\"
ninja -j12 strata > /out/_n.log 2>&1; rc=\$?; echo \"[$n] NINJA_RC=\$rc\"; grep -m4 'error:' /out/_n.log
md5sum /out/strata 2>/dev/null; exit \$rc"
}

for spec in "llama_k13 c49edf0 build-k13" "llama_k10 4c1004c build-k10"; do
  set -- $spec; n=$1; sha=$2; out=$3
  mk "$n" "$sha" || exit 5
  try_build "$n" "$out" /home/albus/strata166/w1031/src-v090
  rc=$?
  if [ "$rc" -ne 0 ] && grep -q "new_pool_for_device" "/home/albus/strata166/$out/_n.log" 2>/dev/null; then
    echo "[$n] retry with old-pool glue (src-a3)"
    try_build "$n" "$out" /home/albus/strata166/w1031/src-a3
  fi
done
