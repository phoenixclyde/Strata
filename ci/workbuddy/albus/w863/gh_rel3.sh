#!/bin/bash
cd /home/albus/strata166/pr/strata-fork || exit 1
echo "=== remote.origin.fetch (why only 2 branches track) ==="
git config --get-all remote.origin.fetch
echo "=== remote.upstream.fetch ==="
git config --get-all remote.upstream.fetch
echo
echo "=== fetch every origin branch into remote-tracking refs ==="
timeout 240 git fetch origin '+refs/heads/*:refs/remotes/origin/*' --prune 2>&1 | tail -6
echo
echo "=== now the picture ==="
git for-each-ref --format='%(refname:short) %(objectname:short)' refs/remotes/origin | sort
echo
A=origin/gfx906/0.2.9-mi50
echo "=== HEAD(642de24f) vs $A ==="
echo -n "merge-base: "; git merge-base HEAD "$A" | cut -c1-12
echo "-- on HEAD, not in A --"; git log --oneline "$A"..HEAD | head -20
echo "-- on A, not in HEAD --"; git log --oneline HEAD.."$A" | head -20
echo
echo "=== $A vs upstream/main ==="
echo -n "behind by: "; git rev-list --count "$A"..upstream/main
echo -n "ahead by: "; git rev-list --count upstream/main.."$A"
echo "--- upstream commits we lack ---"; git log --oneline "$A"..upstream/main | head -20
