#!/bin/bash
set -u
B=~/strata166/gfx029-build

echo "=== A. 看 build.ninja 依赖哪些文件（决定要 touch 谁） ==="
grep -A3 "^build build.ninja:" $B/build.ninja 2>/dev/null | head -8 | cut -c1-200

echo
echo "=== B. 把 build.ninja 与其依赖的 mtime 推到未来 ==="
touch -d "2026-11-06 00:00:00" $B/build.ninja 2>/dev/null && echo "  build.ninja -> $(stat -c%y $B/build.ninja)"
for f in CMakeCache.txt CMakeFiles/rules.ninja; do
  [ -f "$B/$f" ] && touch -d "2026-11-06 00:00:00" "$B/$f" && echo "  $f -> $(stat -c%y $B/$f)"
done
# CMakeFiles 下的 .cmake 也一并推后（避免别的触发点）
find $B/CMakeFiles -maxdepth 1 -name "*.cmake" -newer $B/build.ninja 2>/dev/null | head -3

echo
echo "=== C. 只链接（不编） ==="
docker run --rm -v ~/strata166/work/r77:/src -v $B:/out -w /out strata-gfx906:0.2.9-101 \
  bash -lc "ninja -d explain strata 2>&1 | tail -18; echo RC=\$?" 2>&1 | tail -22
