#!/bin/bash
# 只看 CMake 到底为什么 incomplete（不改任何东西，输出全量）
S=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
docker run --rm --security-opt label=disable -v "$S":/src -v "$B":/out strata-gfx906:0.2.9-101 \
  bash -lc 'cmake -S /src -B /out 2>&1 | tail -40' 2>&1 | tail -42
