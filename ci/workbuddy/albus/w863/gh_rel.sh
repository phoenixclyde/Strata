#!/bin/bash
cd /home/albus/strata166/pr/strata-fork || exit 1
echo "=== fetch upstream (gh-proxy) ==="
timeout 180 git fetch upstream --prune 2>&1 | tail -5
echo
echo "=== upstream/main tip ==="
git log --oneline -6 upstream/main 2>&1
echo
echo "=== our local HEAD 642de24f: where does it sit? ==="
git log --oneline -6 HEAD
echo
echo "=== is 642de24f an ancestor of origin/gfx906-0.2.9-mi50 (aef9d256)? ==="
git merge-base --is-ancestor 642de24f aef9d256 && echo "YES ancestor" || echo "NO"
echo "=== merge-base of HEAD and aef9d256 ==="
git merge-base HEAD aef9d256 | cut -c1-12
echo "=== commits on HEAD not in aef9d256 ==="
git log --oneline aef9d256..HEAD | head -12
echo "=== commits on aef9d256 not in HEAD ==="
git log --oneline HEAD..aef9d256 | head -12
echo
echo "=== how far behind is aef9d256 vs upstream/main ==="
git rev-list --count aef9d256..upstream/main 2>&1
echo "=== upstream commits we do not have ==="
git log --oneline aef9d256..upstream/main 2>&1 | head -20
