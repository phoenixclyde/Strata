#!/bin/bash
# W839-30b 直接跑二进制（容器内路径 /data/bin）
IMG=strata-gfx906:0.2.8p2
B=/data/bin/strata-0.1.54n3
echo "=== A) TUNED=1 ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  "$IMG" bash -lc "$B --serve --pack /nope 2>&1 | head -12"
echo
echo "=== B) 不带 TUNED（精确表 2 项应打印）==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  "$IMG" bash -lc "$B --serve --pack /nope 2>&1 | head -10"
echo
echo "=== C) DEFAULTS=0 全关 ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 -e STRATA_GFX906_DEFAULTS=0 \
  "$IMG" bash -lc "$B --serve --pack /nope 2>&1 | head -8"
echo
echo "=== D) 对照 n2（应完全无横幅）==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  "$IMG" bash -lc "/data/bin/strata-0.1.54n2 --serve --pack /nope 2>&1 | head -8"
