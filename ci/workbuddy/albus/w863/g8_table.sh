#!/bin/bash
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== tag v0.2.9 really points at upstream/main? (annotated tags need ^{commit}) ==="
git rev-parse v0.2.9^{commit} | cut -c1-12
git rev-parse upstream/main | cut -c1-12
[ "$(git rev-parse v0.2.9^{commit})" = "$(git rev-parse upstream/main)" ] && echo "YES v0.2.9 == upstream/main" || echo "NO"
echo
echo "=== local branches vs origin (ahead/behind) ==="
printf "%-28s %-10s %-10s %s\n" BRANCH LOCAL ORIGIN AHEAD/BEHIND
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  L=$(git rev-parse --short "$b")
  if git rev-parse --verify -q "origin/$b" >/dev/null; then
    O=$(git rev-parse --short "origin/$b")
    AB=$(git rev-list --left-right --count "$b...origin/$b" 2>/dev/null | awk '{print "ahead "$1" / behind "$2}')
  else
    O="-"; AB="not on origin"
  fi
  printf "%-28s %-10s %-10s %s\n" "$b" "$L" "$O" "$AB"
done
echo
echo "=== the MI50 line, end to end ==="
echo "upstream/main  $(git rev-parse --short upstream/main)"
echo "aef9d256       (v0.2.8 patches replayed onto v0.2.9)"
echo "78fa2a72       (W863 waves-rows table + env switch)  <= HEAD"
git log --oneline upstream/main..gfx906/0.2.9-mi50
echo
echo "=== the A/B that is running ==="
tail -8 /home/albus/strata166/w863/specminp_20261101_152024.txt 2>/dev/null
