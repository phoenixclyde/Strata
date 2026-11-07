#!/bin/bash
# W835: fetch KI upstream incrementally on 166 (correct remote name) and diff
K=/home/albus/routeK/base/KIntegrated-mobydick
cd $K || exit 1
echo "=== A. remotes / before ==="
git remote -v | head -3
git rev-parse --short HEAD
git log -1 --format='%ad %s' --date=short
echo
echo "=== B. fetch ==="
timeout 600 git fetch origin main --depth=600 2>&1 | tail -8
echo
echo "=== C. FETCH_HEAD ==="
git log --oneline -1 FETCH_HEAD 2>/dev/null
echo "behind by: $(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null || echo '?') commits"
echo
echo "=== D. new/all files under csrc/rocm + csrc/gfx906_fa since our HEAD ==="
git diff --name-status HEAD..FETCH_HEAD -- csrc/rocm csrc/gfx906_fa vllm/gfx906_fa 2>/dev/null | head -40
echo
echo "=== E. overall change size (gfx906 dirs) ==="
git diff --stat HEAD..FETCH_HEAD -- csrc/rocm csrc/gfx906_fa docs/gfx906 2>/dev/null | tail -25
echo
echo "=== F. docs/gfx906 listing at FETCH_HEAD ==="
git ls-tree --name-only FETCH_HEAD docs/gfx906/ 2>/dev/null | head -40
