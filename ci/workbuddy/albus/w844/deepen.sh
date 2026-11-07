set +e
cd /home/albus/strata166/gfx906
echo "=== 当前是否 shallow ==="
git rev-parse --is-shallow-repository
echo "=== 加深历史（~40 提交） ==="
timeout 240 git fetch --deepen=40 upstream main 2>&1 | tail -3
echo "=== 再判 ==="
echo "upstream/main = $(git rev-parse --short upstream/main)"
echo -n "merge-base    = "; git merge-base HEAD upstream/main | cut -c1-8
echo -n "上游领先 = "; git rev-list --count HEAD..upstream/main
echo -n "我们领先 = "; git rev-list --count upstream/main..HEAD
echo "=== 我们的提交（全部） ==="
git log --oneline upstream/main..HEAD | head -14
