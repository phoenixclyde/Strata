#!/bin/bash
# W835: inventory + read the highest-value upstream gfx906 docs
K=/home/albus/routeK/base/KIntegrated-mobydick
cd $K || exit 1
echo "=== A. docs/gfx906 file sizes at FETCH_HEAD (top 30) ==="
git ls-tree -r -l FETCH_HEAD docs/gfx906/ 2>/dev/null | awk '{printf "%8s  %s\n", $4, $5}' | sort -rn | head -30
echo
echo "=== B. DEAD-ENDS.md ==="
git show FETCH_HEAD:docs/gfx906/DEAD-ENDS.md 2>/dev/null | head -120
