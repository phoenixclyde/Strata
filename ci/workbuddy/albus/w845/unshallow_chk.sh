set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
echo "now=$(date +%H:%M:%S)"
echo -n "is-shallow = "; git rev-parse --is-shallow-repository
echo -n ".git 体积 = "; du -sh "$(git rev-parse --git-common-dir)" 2>/dev/null | cut -f1
echo -n "仍在跑: "; pgrep -af "git fetch --unshallow" | head -2
echo "--- v0.2.9 父提交: $(git rev-list --parents -1 v0.2.9 | cut -c1-100)"
echo -n "merge-base(HEAD, up/main) = "; git merge-base HEAD upstream/main 2>/dev/null | cut -c1-10 || echo "(空)"
echo -n "upstream/main = "; git rev-parse --short upstream/main
echo -n "HEAD = "; git rev-parse --short HEAD
