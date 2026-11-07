#!/bin/bash
# 梯子第 1 步（历史顺序，单条累加）：pin + e9f824d + 748d422 + 272aad8 + 8b2fbaf + fc9ce6b
# 目标：把 #29953（MMQ OOB 修复 + J_best 重构）这一条单独顶上去测。粘合层用 pin 原版（J_best 槽技巧）。
set -u
IMG=strata-gfx906:0.2.11-101
SRC=/home/albus/strata166/pr/strata-fork
LL=/home/albus/strata166/w1031/llama_p5
OUT=/home/albus/strata166/build-p5
P=/home/albus/strata166/w1031/picks

rm -rf "$LL"; cp -a /home/albus/strata166/ref/llama_3cf0325 "$LL"
cd "$LL" || exit 3
for c in e9f824d 748d422 272aad8 8b2fbaf fc9ce6b; do
  git apply -p1 "$P/$c.patch" || { echo "APPLY FAILED $c"; exit 4; }
  echo "applied $c"
done
grep -c "J_best" ggml/src/ggml-cuda/mmq.cuh

mkdir -p "$OUT"; cp -f /home/albus/strata166/build-r28/CMakeCache.txt "$OUT/CMakeCache.txt" 2>/dev/null
docker rm -f p5build >/dev/null 2>&1
docker run --rm --name p5build --device=/dev/kfd --device=/dev/dri \
  -v "$SRC":/src -v "$LL":/llama.cpp -v "$OUT":/out "$IMG" bash -lc '
cd /out; cmake -S /src -B /out -G Ninja > /out/_c.log 2>&1; echo "CMAKE_RC=$?"
ninja -j12 strata > /out/_n.log 2>&1; rc=$?; echo "NINJA_RC=$rc"; grep -m5 "error:" /out/_n.log
md5sum /out/strata 2>/dev/null; exit "$rc"'
