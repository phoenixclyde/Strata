#!/bin/bash
# W836: three-way verdict for every differing file: old residue vs our patch vs upstream move
W=/home/albus/strata166/gfx906
S=/home/albus/strata166/src028
cd "$W" || exit 1
echo "=== fetch v0.2.7.1 for the residue test ==="
timeout 300 git fetch ghup tag v0.2.7.1 --no-tags 2>&1 | tail -2
echo "v0.2.7.1 = $(git rev-parse v0.2.7.1^{commit} 2>/dev/null | cut -c1-8)"
echo
printf "%-52s %-10s %-10s %s\n" FILE "vs main" "vs 0.2.7.1" VERDICT
RESIDUE=0; OURS=0
for f in $(git ls-files | grep -E '^(src/|include/|serve/|apps/|CMakeLists\.txt$|cmake/)' ); do
  [ -f "$S/$f" ] || continue
  cmp -s "$W/$f" "$S/$f" && continue
  # compare src028 against the old tag
  old=$(git cat-file -e v0.2.7.1:$f 2>/dev/null && git show v0.2.7.1:$f 2>/dev/null | md5sum | cut -d' ' -f1)
  cur=$(md5sum "$S/$f" | cut -d' ' -f1)
  if [ -n "$old" ] && [ "$old" = "$cur" ]; then
    v="RESIDUE(0.2.7.1)"; RESIDUE=$((RESIDUE+1))
  else
    v="**OURS**"; OURS=$((OURS+1))
  fi
  printf "%-52s %-10s %-10s %s\n" "$f" "diff" "${old:+has}" "$v"
done
echo
echo "SUMMARY: residue(old-version leftovers) = $RESIDUE ; ours = $OURS"
