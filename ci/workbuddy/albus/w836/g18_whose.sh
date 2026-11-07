#!/bin/bash
# W836: for every differing file, decide: upstream moved it, or WE changed it?
W=/home/albus/strata166/gfx906
S=/home/albus/strata166/src028
cd "$W" || exit 1
echo "file | upstream v0.2.8->main | verdict"
echo "-----|----------------------|--------"
OURS=0
for f in $(git ls-files | grep -E '^(src/|include/|serve/|apps/|CMakeLists\.txt$|cmake/)' ); do
  [ -f "$S/$f" ] || continue
  cmp -s "$W/$f" "$S/$f" && continue
  # does upstream move this file between the tag and main?
  up=$(git diff --numstat v0.2.8 ghup/main -- "$f" 2>/dev/null | awk '{print $1"+"$2"-"}')
  if [ -z "$up" ]; then
    echo "  $f | (untouched) | **OURS**"
    OURS=$((OURS+1))
  fi
done
echo
echo "OURS (upstream never touched, yet src028 differs) = $OURS"
echo
echo "=== now show what OUR change in each of those actually is (first 6 lines) ==="
for f in $(git ls-files | grep -E '^(src/|include/|serve/|apps/|CMakeLists\.txt$|cmake/)' ); do
  [ -f "$S/$f" ] || continue
  cmp -s "$W/$f" "$S/$f" && continue
  up=$(git diff --numstat v0.2.8 ghup/main -- "$f" 2>/dev/null)
  [ -n "$up" ] && continue
  echo "--- $f"
  diff -u "$W/$f" "$S/$f" 2>/dev/null | grep -E '^[+-][^+-]' | head -6
done
