#!/bin/bash
set -u
W=~/strata166/work/r77
cd "$W" || exit 1
echo "=== decode_ms 后的 wait_commit ==="
grep -n "decode_ms = std::chrono" src/program/generate.cpp | head -5
L=$(grep -n "decode_ms = std::chrono" src/program/generate.cpp | head -1 | cut -d: -f1)
[ -n "$L" ] && sed -n "$L,$((L+8))p" src/program/generate.cpp
echo
echo "=== 全部 include ==="
grep -n "^#include" src/program/generate.cpp | head -40
