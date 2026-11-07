#!/bin/bash
cd /home/albus/strata166/pr/strata-fork || exit 1
A=origin/gfx906/0.2.9-mi50
echo "=== is our local HEAD 642de24f published anywhere? ==="
echo -n "local branches containing it: "; git branch --contains 642de24f | tr '\n' ' '; echo
echo -n "remote branches containing it: "; git branch -r --contains 642de24f | tr '\n' ' '; echo
echo
echo "=== content diff: published 0.2.9-mi50 tip vs local HEAD (uncommitted changes excluded) ==="
git diff --stat "$A" HEAD | tail -25
echo
echo "=== does the working tree add anything on top? ==="
git diff --stat HEAD
echo
echo "=== our 8 local commits' subjects vs the published squash ==="
git log --oneline upstream/main..HEAD
echo "--- published ---"
git log --format='%h %s' upstream/main.."$A"
echo
echo "=== upstream/main tip sha (full) ==="
git rev-parse upstream/main
git rev-parse origin/gfx906/0.2.9-mi50
git rev-parse HEAD
