#!/bin/bash
# W838: prove nothing went to upstream, and make that structurally impossible
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1

echo "=== A. current remotes (note the push column) ==="
git remote -v

echo
echo "=== B. what each remote actually points at ==="
for r in $(git remote); do
  echo "  $r:"
  echo "    fetch: $(git config --get remote.$r.url)"
  echo "    push : $(git config --get remote.$r.pushurl || git config --get remote.$r.url)"
done

echo
echo "=== C. refs we published (only origin/* should exist, and only ours) ==="
git for-each-ref --format='  %(refname)  %(objectname:short)' refs/remotes | head -20

echo
echo "=== D. reflog of our branch: where did commits go? ==="
git reflog show gfx906/0.2.8-mi50 2>/dev/null | head -6

echo
echo "=== E. was any push ever attempted at an upstream URL? (shell history) ==="
grep -n "push" /home/albus/.bash_history 2>/dev/null | grep -iE "Niko1221|upstream|ghup" | head -5 || echo "  (no such line in .bash_history)"
