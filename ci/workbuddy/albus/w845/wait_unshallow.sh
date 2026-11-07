set +e
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
for i in $(seq 1 24); do
  pgrep -f "git fetch --unshallow" >/dev/null || break
  sleep 15
done
echo "now=$(date +%H:%M:%S)"
echo -n "is-shallow = "; git rev-parse --is-shallow-repository
echo -n ".git 体积 = "; du -sh "$(git rev-parse --git-common-dir)" 2>/dev/null | cut -f1
echo "--- 仍有进程: "; pgrep -af "git fetch" | head -3
echo "--- v0.2.9 父提交（应出现第二段 sha）: $(git rev-list --parents -1 v0.2.9 | cut -c1-110)"
echo -n "shallow 文件行数 = "; wc -l < "$(git rev-parse --git-common-dir)/shallow" 2>/dev/null
echo -n "merge-base = "; git merge-base HEAD upstream/main | cut -c1-10
echo "--- 尝试 rebase（应为 no-op）:"
git rebase upstream/main 2>&1 | tail -3
echo -n "HEAD = "; git rev-parse --short HEAD
echo "--- 历史连通性自检：从 HEAD 能不能走到 100 个提交前的祖先"
git rev-list --count HEAD 2>/dev/null
