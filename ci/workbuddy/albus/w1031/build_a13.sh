#!/bin/bash
# 逐条试：把 MMQ 头按「历史检查点」整体取回，定位 0.9.0 的 3.8% 是哪一段引入的。
#   A1 = ggml-cuda @ fc9ce6b (#29953 J_best/OOB + 更早的 musa/NVFP4/W4A4)   粘合层：pin 原样
#   A3 = ggml-cuda @ c49edf0 (#30168 prec + #30553 + #30837 + #29927 + #29948 GLU 融合)  粘合层：prec 补丁
set -u
IMG=strata-gfx906:0.2.11-101
BASE=/home/albus/strata166/ref/llama_b12110
CL=/home/albus/strata166/w1031/lcpp

mk () {  # mk <name> <sha>
  local n=$1 sha=$2 LL=/home/albus/strata166/w1031/$1
  rm -rf "$LL"; cp -a "$BASE" "$LL"
  rm -rf "$LL/ggml/src/ggml-cuda"
  mkdir -p "$LL/ggml/src/ggml-cuda"
  ( cd "$CL" && git archive "$sha" ggml/src/ggml-cuda 2>/dev/null || git ls-tree -r --name-only "$sha" ggml/src/ggml-cuda | while read -r f; do mkdir -p "$LL/$(dirname "$f")"; git show "$sha:$f" > "$LL/$f"; done )
}
# git archive 在 blobless 浅克隆里可能失败，退回逐个 show
mk llama_a1 fc9ce6b || exit 5
mk llama_a3 c49edf0 || exit 5
echo "A1 mmq.cuh: $(md5sum ~/strata166/w1031/llama_a1/ggml/src/ggml-cuda/mmq.cuh | cut -c1-12)  files=$(find ~/strata166/w1031/llama_a1/ggml/src/ggml-cuda -type f | wc -l)"
echo "A3 mmq.cuh: $(md5sum ~/strata166/w1031/llama_a3/ggml/src/ggml-cuda/mmq.cuh | cut -c1-12)  files=$(find ~/strata166/w1031/llama_a3/ggml/src/ggml-cuda -type f | wc -l)"

# glue trees
rm -rf /home/albus/strata166/w1031/src-a3
cp -a /home/albus/strata166/w1031/src-v090 /home/albus/strata166/w1031/src-a3
python3 - <<'PY'
import pathlib
p=pathlib.Path("/home/albus/strata166/w1031/src-a3/src/prefill/ggml_cuda_host.cu"); s=p.read_text()
new="std::unique_ptr<ggml_cuda_pool> ggml_backend_cuda_context::new_pool_for_device(ggml_backend_cuda_context &, int, int) {"
old="std::unique_ptr<ggml_cuda_pool> ggml_backend_cuda_context::new_pool_for_device(int, int) {"
assert s.count(new)==1
p.write_text(s.replace(new,old,1)); print("src-a3: pool back to old signature")
PY

build () {  # build <name> <src> <out>
  local n=$1 SRC=$2 OUT=/home/albus/strata166/$3 LL=/home/albus/strata166/w1031/$1
  mkdir -p "$OUT"; cp -f /home/albus/strata166/build-v090/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
  docker rm -f "b_$n" >/dev/null 2>&1
  docker run --rm --name "b_$n" --device=/dev/kfd --device=/dev/dri \
    -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc "
cd /out; cmake -S /src -B /out -G Ninja > /out/_c.log 2>&1; echo \"[$n] CMAKE_RC=\$?\"
ninja -j12 strata > /out/_n.log 2>&1; rc=\$?; echo \"[$n] NINJA_RC=\$rc\"; grep -m4 'error:' /out/_n.log
md5sum /out/strata 2>/dev/null; exit \$rc"
}
build llama_a1 /home/albus/strata166/pr/strata-fork build-a1
build llama_a3 /home/albus/strata166/w1031/src-a3 build-a3
