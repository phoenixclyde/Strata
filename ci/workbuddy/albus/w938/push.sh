#!/bin/bash
set -u
cd /home/albus/strata166/pr/strata-fork || exit 1

echo "=== 1) 先 fetch，确保 lease 判断基于最新远端 ==="
timeout 90 git fetch origin --tags 2>&1 | tail -3
echo "remote gfx906/mi50 = $(git rev-parse --short origin/gfx906/mi50)"

echo
echo "=== 2) 推主线（force-with-lease：远端若被别人改过就拒绝） ==="
timeout 120 git push --force-with-lease origin gfx906/mi50 2>&1 | tail -6

echo
echo "=== 3) 推 main（快进） ==="
timeout 120 git push origin main 2>&1 | tail -3

echo
echo "=== 4) 推 r28 tag 与 archive tag ==="
timeout 120 git push origin mi50-0.2.10-r28 2>&1 | tail -3
timeout 120 git push origin archive/r54-port archive/exp-R55-swizzle archive/bench-mi50-32gb-262k archive/w863-main 2>&1 | tail -4

echo
echo "=== 5) 校验远端与本地一致 ==="
timeout 60 git ls-remote origin refs/heads/gfx906/mi50 refs/tags/mi50-0.2.10-r28 2>&1
echo "local  HEAD          = $(git rev-parse HEAD)"
echo "local  tag r28       = $(git rev-parse mi50-0.2.10-r28)"
