#!/bin/bash
# W863 · 归档后清理：每条先打 archive tag，再删远端与本地
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1

KEEP="gfx906/mi50 main bench-mi50-32gb-262k rc/0.1.30"
DEL="gfx906/0.2.9-mi50 gfx906/0.2.8-mi50 gfx906/hipblaslt-vega20 gfx906/mmq-plan-banner gfx906/routed-stream amd-monitor-name-consistency amd-monitor-pcie-link gfx906-cpu-share-guard web-sparkline-axis-floor gfx906-build-fixes-402"

echo "=== 1. 打归档 tag（一个分支一个 tag，指到它原来的顶端）==="
for b in $DEL; do
  t="archive/$(echo "$b" | tr '/' '-')"
  sha=$(git rev-parse --short "origin/$b" 2>/dev/null)
  git tag -f "$t" "origin/$b" >/dev/null 2>&1 && echo "  $t -> $sha"
done
echo
echo "=== 2. 推 tag（归档留痕，只在 fork）==="
timeout 180 git push origin --tags 2>&1 | tail -4
echo
echo "=== 3. 删远端分支 ==="
for b in $DEL; do
  timeout 60 git push origin --delete "$b" 2>&1 | grep -E "deleted|error" | head -1
done
echo
echo "=== 4. 删本地同名分支 ==="
git checkout gfx906/mi50 >/dev/null 2>&1
for b in $DEL; do
  git branch -D "$b" >/dev/null 2>&1 && echo "  deleted local $b"
done
git branch --list 'gfx906/0.2*' 2>/dev/null
echo
echo "=== 5. 结果 ==="
echo "--- remote heads ---"
git ls-remote --heads origin | awk '{print substr($1,1,8), $2}' | sed 's#refs/heads/##'
echo "--- local branches ---"
git branch --format='%(refname:short) %(objectname:short)'
echo "--- archive tags ---"
git tag -l 'archive/*' | head -12
echo -n "--- working tree dirty files: "; git status --porcelain | wc -l
