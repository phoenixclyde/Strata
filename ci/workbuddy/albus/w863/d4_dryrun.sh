#!/bin/bash
# W863 · 重编引擎（增量，逐字沿用 gfx029-build 的 ninja 配置；不改任何 CMake 选项）
set -u
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
IMG=strata-gfx906:0.2.9-101

echo "=== dry run: what would ninja rebuild? ==="
docker run --rm --security-opt label=disable -v "$S":/src -v "$B":/build "$IMG" bash -lc '
  cd /build || exit 1
  ninja -n strata 2>&1 | tail -12
  echo "--- count ---"
  ninja -n strata 2>&1 | grep -c "^\["
' 2>&1 | tail -20
