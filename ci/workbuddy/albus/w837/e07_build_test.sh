#!/bin/bash
# W837: compile and run arch_defaults_test on its own (no GPU, no full build)
W=/home/albus/strata166/gfx906
IMG=strata-gfx906:0.2.8p2
docker run --rm --security-opt label=disable -v "$W":/src "$IMG" bash -lc '
  cd /src || exit 1
  echo "=== compile ==="
  g++ -std=c++17 -O1 -I include -o /tmp/adt \
      src/core/arch_defaults_test.cpp src/core/arch_defaults.cpp 2>&1 | head -25
  rc=${PIPESTATUS[0]}
  echo "compile rc=$rc"
  [ -x /tmp/adt ] || { echo "NO BINARY"; exit 1; }
  echo
  echo "=== run ==="
  /tmp/adt; echo "run rc=$?"
' 2>&1 | tail -30
