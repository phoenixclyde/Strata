set +e
cd /home/albus/strata166/gfx029 || exit 1
timeout 120 git fetch origin "refs/heads/gfx906/0.2.9-mi50:refs/remotes/origin/gfx906/0.2.9-mi50" 2>&1 | tail -3
git branch --set-upstream-to=origin/gfx906/0.2.9-mi50 gfx906/0.2.9-mi50 2>&1 | tail -2
echo "--- 跟踪状态:"
git for-each-ref refs/remotes/origin --format='%(refname:short) %(objectname:short)' | grep 0.2.9
git branch -vv | grep 0.2.9
echo "--- 本地 vs 远端:"; echo "  local=$(git rev-parse --short HEAD)  remote=$(git rev-parse --short origin/gfx906/0.2.9-mi50 2>/dev/null)"
echo "--- 能否 fast-forward（本地应已含远端）:"; git rev-list --left-right --count origin/gfx906/0.2.9-mi50...HEAD
