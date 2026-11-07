#!/bin/bash
# W839-30 直接跑二进制，看架构横幅（不经过 server.py）
IMG=strata-gfx906:0.2.8p2
B=/home/albus/strata166/data/bin/strata-0.1.54n3
echo "=== A) TUNED=1 ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 \
  "$IMG" bash -lc "$B --serve --pack /nope 2>&1 | head -14"
echo
echo "=== B) 不带 TUNED（精确表应在全空时给出 2 项）==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -v /home/albus/strata166/data:/data \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 \
  "$IMG" bash -lc "$B --serve --pack /nope 2>&1 | head -10"
echo
echo "=== C) 关表 STRATA_GFX906_DEFAULTS=0 ==="
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add video \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_GFX906_TUNED=1 -e STRATA_GFX906_DEFAULTS=0 \
  "$IMG" bash -lc "$B --serve --pack /nope 2>&1 | head -8"
