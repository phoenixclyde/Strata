#!/bin/bash
# W836: where does our code live, and what is tracked?
echo "=== A. is src028 a git repo? ==="
S=/home/albus/strata166/src028
ls -d $S/.git 2>/dev/null && git -C $S log --oneline -1 2>/dev/null || echo "  src028: NOT a git repo"
echo
echo "=== B. our fork tree ==="
F=/home/albus/strata166/pr/strata-fork
ls -d $F 2>/dev/null || echo "  fork dir missing"
if [ -d "$F/.git" ]; then
  echo "--- remotes ---"; git -C $F remote -v | head -4
  echo "--- branches ---"; git -C $F branch -a | head -12
  echo "--- HEAD ---"; git -C $F log --oneline -1
  echo "--- status (first 12) ---"; git -C $F status --porcelain | head -12
  echo "--- how far from upstream ---"
  git -C $F log --oneline -3 origin/main 2>/dev/null || echo "  no origin/main"
  echo "--- tags near 0.2.8 ---"; git -C $F tag --list "v0.2.8*" 2>/dev/null
fi
echo
echo "=== C. any other strata checkouts on 166 ==="
find /home/albus -maxdepth 3 -name ".git" -type d 2>/dev/null | xargs -r -n1 dirname | while read p; do
  u=$(git -C "$p" config --get remote.origin.url 2>/dev/null)
  case "$u" in *Strata*) echo "  $p | $u | $(git -C $p rev-parse --abbrev-ref HEAD 2>/dev/null)";; esac
done
echo
echo "=== D. our local patch inventory (the thing that must be versioned) ==="
cat /home/albus/strata166/patches/LOCAL_PATCHES.tsv 2>/dev/null || ls /home/albus/strata166/patches/ 2>/dev/null | head
echo
echo "=== E. src028: what differs from a pristine v0.2.8? (top-level only, excluding build/third_party) ==="
ls -la $S | head -6
