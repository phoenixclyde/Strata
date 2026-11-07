#!/bin/bash
# W836: exhaustive diff between the branch tree (source of truth) and src028 (build tree)
W=/home/albus/strata166/gfx906
S=/home/albus/strata166/src028
cd "$W" || exit 1
echo "=== files that differ between branch tree and src028 (source dirs only) ==="
n=0
for f in $(git ls-files | grep -E '^(src/|include/|serve/|apps/|qm/|tools/|CMakeLists\.txt$|cmake/)' ); do
  [ -f "$S/$f" ] || { echo "  ONLY-IN-BRANCH $f"; n=$((n+1)); continue; }
  if ! cmp -s "$W/$f" "$S/$f"; then
    echo "  DIFF $f"
    n=$((n+1))
  fi
done
echo "  total differing: $n"
echo
echo "=== and the reverse: files in src028 that the branch does not have (source dirs) ==="
cd "$S" || exit 1
git -C "$W" ls-files > /tmp/branch_files.txt
find src include serve -type f \( -name '*.cpp' -o -name '*.cu' -o -name '*.cuh' -o -name '*.hpp' -o -name '*.h' -o -name '*.py' -o -name '*.js' -o -name '*.css' \) 2>/dev/null \
  | grep -vE '\.bak|build-' | sort > /tmp/src028_files.txt
comm -13 <(sort /tmp/branch_files.txt) /tmp/src028_files.txt | head -15
echo "  (above are files we added locally; empty = none)"
