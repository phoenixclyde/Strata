#!/bin/bash
# W838: fetching must still work (we track upstream, we just never write to it)
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. fetch from upstream still works ==="
timeout 300 git fetch ghup main --depth=1 --no-tags 2>&1 | tail -3
echo "  ghup/main = $(git rev-parse --short ghup/main 2>&1)"
timeout 120 git ls-remote upstream 2>/dev/null | head -2 || echo "  (ssh ls-remote to upstream: no output)"
echo
echo "=== B. our branch is intact ==="
git rev-parse --abbrev-ref HEAD
git log --oneline -1
echo "  ahead of upstream: $(git rev-list --count ghup/main..HEAD 2>&1)"
echo
echo "=== C. push to our own fork still works (dry run) ==="
git push --dry-run origin gfx906/0.2.8-mi50 2>&1 | tail -3
