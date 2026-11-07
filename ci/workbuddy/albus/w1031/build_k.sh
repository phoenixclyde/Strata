#!/bin/bash
# K 系列：0.9.0 的树（ggml.h / ggml-cpu / ggml-base 都是 0.9.0），只把 MMQ 的那一小撮头换成**某个检查点**的版本。
# 这样每一步都是"完整可运行"的组合，不会像 p5 那样新旧混搭。
#   K10 = mmq 头 @ 4c1004c（含 #29953/#30168/#30553，**不含** #29948 GLU 融合）
#   K13 = mmq 头 @ c49edf0（含 #29948 GLU 融合）
set -u
IMG=strata-gfx906:0.2.11-101
BASE=/home/albus/strata166/ref/llama_b12110
CL=/home/albus/strata166/w1031/lcpp
SRC=/home/albus/strata166/w1031/src-a3
FILES="mmq.cuh mmq-load-tiles.cuh mmq-vec-dot.cuh vecdotq.cuh quantize.cu quantize.cuh mma.cuh dequantize.cuh common.cuh"

mk () {  # mk <name> <sha>
  local n=$1 sha=$2 LL=/home/albus/strata166/w1031/$1
  rm -rf "$LL"; cp -a "$BASE" "$LL"
  for f in $FILES; do
    ( cd "$CL" && git show "$sha:ggml/src/ggml-cuda/$f" ) > "$LL/ggml/src/ggml-cuda/$f" || { echo "fetch failed $sha/$f"; exit 4; }
  done
  echo "$n: mmq.cuh=$(md5sum $LL/ggml/src/ggml-cuda/mmq.cuh | cut -c1-10) common.cuh=$(md5sum $LL/ggml/src/ggml-cuda/common.cuh | cut -c1-10)"
}

# glue: prec 补丁 + 旧的 pool 签名（这些检查点的 common.cuh 还是旧 API）
rm -rf "$SRC"; cp -a /home/albus/strata166/w1031/src-v090 "$SRC"
python3 - <<'PY'
import pathlib
p=pathlib.Path("/home/albus/strata166/w1031/src-a3/src/prefill/ggml_cuda_host.cu"); s=p.read_text()
new="std::unique_ptr<ggml_cuda_pool> ggml_backend_cuda_context::new_pool_for_device(ggml_backend_cuda_context &, int, int) {"
old="std::unique_ptr<ggml_cuda_pool> ggml_backend_cuda_context::new_pool_for_device(int, int) {"
assert s.count(new)==1, "pool line not found"
p.write_text(s.replace(new,old,1)); print("glue src-a3 ready")
PY

build () {  # build <name> <out>
  local n=$1 OUT=/home/albus/strata166/$2 LL=/home/albus/strata166/w1031/$1
  mkdir -p "$OUT"; cp -f /home/albus/strata166/build-v090/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
  docker rm -f "b_$n" >/dev/null 2>&1
  docker run --rm --name "b_$n" --device=/dev/kfd --device=/dev/dri \
    -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc "
cd /out; cmake -S /src -B /out -G Ninja > /out/_c.log 2>&1; echo \"[$n] CMAKE_RC=\$?\"
ninja -j12 strata > /out/_n.log 2>&1; rc=\$?; echo \"[$n] NINJA_RC=\$rc\"; grep -m4 'error:' /out/_n.log
md5sum /out/strata 2>/dev/null; exit \$rc"
}

mk llama_k10 4c1004c || exit 5
mk llama_k13 c49edf0 || exit 5
build llama_k10 build-k10
build llama_k13 build-k13
