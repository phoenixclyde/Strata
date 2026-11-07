#!/bin/bash
cd /home/albus/strata166/pr/strata-fork || exit 1
echo "=== fetch origin ==="
timeout 180 git fetch origin --prune 2>&1 | tail -4
echo
echo "=== remote-tracking refs ==="
git branch -r | head -20
echo
A=origin/gfx906/0.2.9-mi50
B=origin/gfx906/0.2.8-mi50
echo "=== HEAD vs $A ==="
echo -n "merge-base: "; git merge-base HEAD "$A" | cut -c1-12
echo "on HEAD not in A:"; git log --oneline "$A"..HEAD | head -15
echo "on A not in HEAD:"; git log --oneline HEAD.."$A" | head -15
echo
echo "=== $A behind upstream/main by: ==="
git rev-list --count "$A"..upstream/main
echo "=== upstream/main not in $A (first 25) ==="
git log --oneline "$A"..upstream/main | head -25
echo
echo "=== how far behind origin/main is upstream/main ==="
git rev-list --count origin/main..upstream/main
echo "=== tags present ==="
git tag --list 'v0.2.*' | tail -5
