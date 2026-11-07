#!/bin/bash
# W839-31 用最小可用参数把启动推进到架构默认段之后
IMG=strata-gfx906:0.2.8p2
echo "=== n3 + TUNED=1，给全必需 flag ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  "$IMG" bash -lc '/data/bin/strata-0.1.54n3 --serve --pack /nope --ple-gguf /nope2 --native /nope3 2>&1 | head -16'
echo
echo "=== 同一命令，n2 对照 ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  "$IMG" bash -lc '/data/bin/strata-0.1.54n2 --serve --pack /nope --ple-gguf /nope2 --native /nope3 2>&1 | head -10'
echo
echo "=== 我们的块与 ple 校验的先后（源码行号）==="
grep -n -- '--ple-gguf is required' /home/albus/strata166/src028/src/program/generate.cpp | head -3
grep -n 'W839 local' /home/albus/strata166/src028/src/program/generate.cpp | head -2
