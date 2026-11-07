#!/bin/bash
# W835: fetch KI upstream incrementally on 166 and see what's new since 6ccbb03
K=/home/albus/routeK/base/KIntegrated-mobydick
cd $K || exit 1
echo "=== A. before ==="
git rev-parse --short HEAD
git log -1 --format='%ad %s' --date=short
echo
echo "=== B. fetch (via gh-proxy remote) ==="
timeout 600 git fetch ghprox main --depth=400 2>&1 | tail -6 || timeout 600 git fetch origin main --depth=400 2>&1 | tail -6
echo "fetch rc=$?"
echo
echo "=== C. after: any new commits? ==="
git log --oneline -1 FETCH_HEAD 2>/dev/null
echo "--- how far behind ---"
git rev-list --count HEAD..FETCH_HEAD 2>/dev/null || echo "?"
echo
echo "=== D. files changed HEAD..FETCH_HEAD (gfx906-related only) ==="
git diff --stat HEAD..FETCH_HEAD -- 'csrc/gfx906_fa' 'csrc/rocm' 'vllm/gfx906_fa' 'docs/gfx906' 2>/dev/null | tail -40
echo
echo "=== E. is there anything NEW in csrc/rocm that we do not have? ==="
git diff --name-status HEAD..FETCH_HEAD -- 'csrc/rocm' 2>/dev/null | head -30
