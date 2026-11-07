#!/bin/bash
# W836: which of our fork branches correspond to PRs, and what do they touch?
F=/home/albus/strata166/pr/strata-fork
cd $F || exit 1
echo "=== A. fetch upstream (incremental) ==="
timeout 600 git fetch upstream main --depth=200 2>&1 | tail -4
echo "upstream/main = $(git rev-parse --short upstream/main 2>/dev/null)"
echo
echo "=== B. our branches: ahead of upstream, and by what ==="
for b in main bench-mi50-32gb-262k gfx906-build-fixes-402 gfx906-cpu-share-guard amd-monitor-pcie-link amd-monitor-name-consistency web-sparkline-axis-floor; do
  if git rev-parse --verify "$b" >/dev/null 2>&1; then
    n=$(git rev-list --count upstream/main.."$b" 2>/dev/null)
    m=$(git rev-list --count "$b"..upstream/main 2>/dev/null)
    echo "  $b : ahead=$n behind=$m  head=$(git rev-parse --short $b)"
    git log --oneline upstream/main.."$b" 2>/dev/null | head -3 | sed 's/^/       /'
  fi
done
echo
echo "=== C. files each branch touches vs upstream/main ==="
for b in bench-mi50-32gb-262k gfx906-build-fixes-402 gfx906-cpu-share-guard; do
  echo "--- $b"
  git diff --name-only upstream/main.."$b" 2>/dev/null | head -12
done
