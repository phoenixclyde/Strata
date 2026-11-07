set +e
cd /home/albus/strata166/gfx906
echo "=== remotes ==="
git remote -v
echo "=== refs ==="
git branch -r | head -10
echo "=== 本地是否已有 upstream ==="
git rev-parse --short upstream/main 2>/dev/null || echo "no upstream/main"
git rev-parse --short origin/main 2>/dev/null || echo "no origin/main"
echo "=== 分支基线 commit 与上游 tag ==="
git log -1 --format='%h %ad %s' --date=short $(git rev-list --max-parents=0 HEAD 2>/dev/null | tail -1) 2>/dev/null | head -1
git describe --tags --always HEAD 2>/dev/null
