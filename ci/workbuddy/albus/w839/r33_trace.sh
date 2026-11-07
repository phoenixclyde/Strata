#!/bin/bash
# W839-33 带 trace 重编 + 直接跑看探针输出
S=/home/albus/strata166/src028
docker rm -f b028r5 >/dev/null 2>&1
docker run -d --name b028r5 --security-opt label=disable \
  -v "$S":/src -w /src strata-gfx906:0.2.8 \
  bash -lc 'ninja -C /src/build-028r -j10 > /src/build-028r5.log 2>&1; echo "EXIT=$?" >> /src/build-028r5.log' >/dev/null
for i in $(seq 1 60); do grep -q 'EXIT=' $S/build-028r5.log 2>/dev/null && break; sleep 10; done
tail -3 $S/build-028r5.log | cut -c1-120
cp "$S/build-028r/strata" /home/albus/strata166/data/bin/strata-0.1.54n3 && chmod +x /home/albus/strata166/data/bin/strata-0.1.54n3
echo "deployed n3 $(md5sum /home/albus/strata166/data/bin/strata-0.1.54n3 | cut -d' ' -f1)"
echo
IMG=strata-gfx906:0.2.8p2
echo "=== TUNED=1 + TRACE=1 ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 -e STRATA_W839_TRACE=1 \
  "$IMG" bash -lc '/data/bin/strata-0.1.54n3 --serve --pack /nope --ple-gguf /nope2 --native /nope3 2>&1 | head -10'
echo
echo "=== 不给 TUNED（应只出精确表 2 项）==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_W839_TRACE=1 \
  "$IMG" bash -lc '/data/bin/strata-0.1.54n3 --serve --pack /nope --ple-gguf /nope2 --native /nope3 2>&1 | head -10'
