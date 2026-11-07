set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "===== [1] 分支与上游现状 ====="
timeout 180 git fetch upstream --tags 2>&1 | tail -3
timeout 120 git fetch origin 2>&1 | tail -2
echo -n "branch      = "; git rev-parse --abbrev-ref HEAD
echo -n "HEAD        = "; git rev-parse --short HEAD
echo -n "HEAD tree   = "; git rev-parse --short HEAD^{tree}
echo -n "upstream/main = "; git rev-parse --short upstream/main
echo -n "v0.2.9 tag  = "; git rev-parse --short v0.2.9
echo -n "origin/ours = "; git rev-parse --short refs/remotes/origin/gfx906/0.2.9-mi50 2>/dev/null
echo -n "ahead/behind upstream: "; git rev-list --left-right --count upstream/main...HEAD
echo -n "ahead/behind origin  : "; git rev-list --left-right --count refs/remotes/origin/gfx906/0.2.9-mi50...HEAD 2>/dev/null
echo "--- 工作区:"; git status --porcelain | head -10; echo -n "dirty 行数 = "; git status --porcelain | wc -l
echo "--- 上游是否前进（main 最新 3 条）:"; git log --oneline -3 upstream/main
echo "--- 我们领先的提交:"; git log --oneline upstream/main..HEAD
