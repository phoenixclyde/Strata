set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "===== [1] 本地状态（不 fetch） ====="
echo -n "branch        = "; git rev-parse --abbrev-ref HEAD
echo -n "HEAD          = "; git rev-parse --short HEAD
echo -n "HEAD tree     = "; git rev-parse HEAD^{tree}
echo -n "upstream/main = "; git rev-parse --short upstream/main
echo -n "origin/ours   = "; git rev-parse --short refs/remotes/origin/gfx906/0.2.9-mi50 2>/dev/null
echo -n "ahead/behind upstream: "; git rev-list --left-right --count upstream/main...HEAD
echo -n "ahead/behind origin  : "; git rev-list --left-right --count refs/remotes/origin/gfx906/0.2.9-mi50...HEAD 2>/dev/null
echo -n "dirty 行数    = "; git status --porcelain | wc -l
echo "--- 是否有 fetch 进程在跑:"; pgrep -af "git.*fetch" | head -3
echo "--- 上次 fetch 的 FETCH_HEAD 时间: $(ls -l --time-style=+%m-%d_%H:%M ../gfx906/.git/FETCH_HEAD 2>/dev/null | awk '{print $6}')"
echo "--- 我们的提交:"; git log --oneline upstream/main..HEAD
