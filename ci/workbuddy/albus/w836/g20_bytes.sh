#!/bin/bash
# W836: history-free verdict. Compare file bytes against the tag trees directly.
W=/home/albus/strata166/gfx906
S=/home/albus/strata166/src028
cd "$W" || exit 1
printf "%-50s %-9s %-9s %s\n" FILE "==0.2.8" "==0.2.7.1" VERDICT
OURS=0; RESIDUE=0; ADVANCED=0
OURS_LIST=""
for f in $(git ls-files | grep -E '^(src/|include/|serve/|apps/|CMakeLists\.txt$|cmake/)' ); do
  [ -f "$S/$f" ] || continue
  cmp -s "$W/$f" "$S/$f" && continue          # same as branch -> not a difference
  cur=$(md5sum "$S/$f" | cut -d' ' -f1)
  h8=$(git show v0.2.8:$f 2>/dev/null | md5sum | cut -d' ' -f1)
  h7=$(git show v0.2.7.1:$f 2>/dev/null | md5sum | cut -d' ' -f1)
  if [ "$cur" = "$h8" ]; then
    ADVANCED=$((ADVANCED+1)); continue          # we are just at 0.2.8; upstream moved on
  elif [ "$cur" = "$h7" ]; then
    RESIDUE=$((RESIDUE+1)); printf "%-50s %-9s %-9s %s\n" "$f" "no" "YES" "RESIDUE"
  else
    OURS=$((OURS+1)); OURS_LIST="$OURS_LIST $f"
    printf "%-50s %-9s %-9s %s\n" "$f" "no" "no" "**OURS**"
  fi
done
echo
echo "SUMMARY  upstream-advanced(=we sit at 0.2.8): $ADVANCED   residue: $RESIDUE   ours: $OURS"
echo
echo "=== OUR files ==="
for f in $OURS_LIST; do echo "  $f"; done
