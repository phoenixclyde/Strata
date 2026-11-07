set +e
cd /home/albus/strata166/gfx906
echo "=== 加 upstream（只 fetch，不配 push）==="
git remote remove upstream 2>/dev/null
git remote add upstream https://gh-proxy.com/https://github.com/Niko1221/Strata.git
timeout 180 git fetch upstream main --depth=1 2>&1 | tail -3
echo "--- remotes:"; git remote -v | grep upstream
echo "=== 基线判定 ==="
echo "upstream/main = $(git rev-parse --short upstream/main 2>/dev/null)"
echo "HEAD          = $(git rev-parse --short HEAD)"
echo -n "merge-base    = "; git merge-base HEAD upstream/main 2>/dev/null | cut -c1-8
echo -n "上游领先我们的提交数 = "; git rev-list --count HEAD..upstream/main 2>/dev/null
echo -n "我们领先上游的提交数 = "; git rev-list --count upstream/main..HEAD 2>/dev/null
echo "=== 我们这 11 个提交 ==="
git log --oneline upstream/main..HEAD 2>/dev/null | head -14
