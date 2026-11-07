set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "now=$(date +%H:%M:%S)"
echo -n "is-shallow = "; git rev-parse --is-shallow-repository
echo -n "status 行数 = "; git status --porcelain | wc -l
echo -n "exclude 尾行: "; tail -2 "$(git rev-parse --git-common-dir)/info/exclude" | tr '\n' '|'
echo
echo -n "HEAD = "; git rev-parse --short HEAD
echo "--- 有没有 git 进程在跑:"; pgrep -af "git (fetch|rebase|gc)" | head -3
echo "--- .git 体积: $(du -sh "$(git rev-parse --git-common-dir)" 2>/dev/null | cut -f1)"
echo "--- 门禁（若已可跑）:"
timeout 120 bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -4
