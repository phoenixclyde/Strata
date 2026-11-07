#!/bin/bash
# S6: 单条移植 #29478（HIP: __vsubss4 -> __vsub4）到 pin 树。这是 41 条里唯一"纯代码生成收益、语义逐字节相同"的一条。
set -u
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/pr/strata-fork
LL=/home/albus/strata166/w1031/llama_pin_vsub4
OUT=/home/albus/strata166/build-vsub4

if [ ! -d "$LL" ]; then
  cp -a /home/albus/strata166/ref/llama_3cf0325 "$LL"
  cd "$LL" && patch -p1 < /tmp/vsub4.patch || exit 5
fi
echo "--- mmq-load-tiles.cuh vs pin:"; md5sum "$LL/ggml/src/ggml-cuda/mmq-load-tiles.cuh" /home/albus/strata166/ref/llama_3cf0325/ggml/src/ggml-cuda/mmq-load-tiles.cuh

mkdir -p "$OUT"; cp -f /home/albus/strata166/build-r28/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
docker rm -f vs4build >/dev/null 2>&1
docker run --rm --name vs4build --device=/dev/kfd --device=/dev/dri \
  -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc '
set -u
cd /out
cmake -S /src -B /out -G Ninja > /out/_c.log 2>&1
rc=$?; echo "CMAKE_RC=$rc"; [ "$rc" -ne 0 ] && tail -8 /out/_c.log && exit "$rc"
ninja -j12 strata > /out/_n.log 2>&1
rc=$?; echo "NINJA_RC=$rc"; grep -m5 "error:" /out/_n.log
md5sum /out/strata 2>/dev/null; ls -l /out/strata 2>/dev/null
exit "$rc"'
