set -u
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
G=$(git rev-parse --git-common-dir)

echo "===== [1] 修 exclude 路径（worktree 的 .git 是文件） ====="
echo "  git-common-dir = $G"
printf '%s\n' "build-029g" "strata" "build-*/" >> "$G/info/exclude"
sort -u "$G/info/exclude" -o "$G/info/exclude"
tail -4 "$G/info/exclude" | sed 's/^/  /'
echo -n "  status 现在剩: "; git status --porcelain | wc -l

echo "===== [2] 门禁复跑（树内已无副本，必须仍 PASS） ====="
bash /home/albus/strata166/tmp/verify_patches.sh 2>&1 | tail -6

echo "===== [3] 补全历史：unshallow（仓库 80 MB，代价可接受） ====="
echo -n "  之前 is-shallow = "; git rev-parse --is-shallow-repository
timeout 480 git fetch --unshallow upstream 2>&1 | tail -3
timeout 240 git fetch upstream --tags 2>&1 | tail -2
echo -n "  之后 is-shallow = "; git rev-parse --is-shallow-repository

echo "===== [4] 现在能不能算 merge-base（rebase 的前提） ====="
echo -n "  merge-base(HEAD, upstream/main) = "; git merge-base HEAD upstream/main | cut -c1-10
echo -n "  上游领先我们的提交数 = "; git rev-list --count HEAD..upstream/main
echo -n "  我们领先上游的提交数 = "; git rev-list --count upstream/main..HEAD
echo "  我们的提交:"; git log --oneline upstream/main..HEAD | sed 's/^/    /'
echo "  v0.2.9 是否真有父提交（不再是 grafted）: $(git rev-list --parents -1 v0.2.9 | cut -c1-90)"

echo "===== [5] 实测 rebase（当前应为 no-op） ====="
git rebase upstream/main 2>&1 | tail -3
echo -n "  HEAD = "; git rev-parse --short HEAD

echo "===== [6] 写一条可复用的 rebase 助手 ====="
cat > /home/albus/strata166/tmp/rebase_gfx906.sh <<'EOS'
#!/bin/bash
# gfx906 分支跟上游：优先 git rebase；浅克隆下自动改用 --onto（不依赖共同祖先的历史连通性）
set -u
D=/home/albus/strata166/gfx029
cd "$D" || exit 1
REF=${1:-upstream/main}
git fetch upstream --tags >/dev/null 2>&1
git fetch upstream >/dev/null 2>&1
if git rev-parse --is-shallow-repository | grep -q true; then
  BASE=$(git rev-parse --short HEAD~1 2>/dev/null)
  echo "shallow repo -> git rebase --onto $REF $BASE"
  git rebase --onto "$REF" "$BASE"
else
  MB=$(git merge-base HEAD "$REF" || true)
  [ -z "$MB" ] && { echo "no merge-base; run: git fetch --unshallow upstream"; exit 2; }
  echo "merge-base=$(echo $MB | cut -c1-8) -> git rebase $REF"
  git rebase "$REF"
fi
git log --oneline --decorate -3
EOS
chmod +x /home/albus/strata166/tmp/rebase_gfx906.sh
echo "  written: /home/albus/strata166/tmp/rebase_gfx906.sh"

echo "===== [7] 最终状态 ====="
git log --oneline --decorate -3 | sed 's/^/  /'
git status --short | head -4
git branch -vv | grep -E "0.2.9|0.2.8" | sed 's/^/  /'
