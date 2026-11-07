#!/bin/bash
# W863 · 分支盘点：每条是否已并入主线（祖先判定 + 内容判定）
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
HEAD_SHA=$(git rev-parse HEAD)
echo "HEAD = $(git rev-parse --short HEAD) on $(git rev-parse --abbrev-ref HEAD)"
echo
printf "%-34s %-9s %-11s %-8s %s\n" BRANCH TIP DATE ANCESTOR NOTE
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -v '^origin$' | sed 's#^origin/##'); do
  s=$(git rev-parse --short "origin/$b")
  d=$(git log -1 --format='%ci' "origin/$b" | cut -c1-10)
  if git merge-base --is-ancestor "origin/$b" HEAD 2>/dev/null; then anc="YES"; else anc="no"; fi
  sub=$(git log -1 --format='%s' "origin/$b" | cut -c1-46)
  printf "%-34s %-9s %-11s %-8s %s\n" "$b" "$s" "$d" "$anc" "$sub"
done
echo
echo "=== 对「no」的分支：把它的成果 cherry 到主线会不会是空的？（看它相对 merge-base 的 diff 有多大）==="
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -v '^origin$' | sed 's#^origin/##'); do
  if ! git merge-base --is-ancestor "origin/$b" HEAD 2>/dev/null; then
    mb=$(git merge-base "origin/$b" HEAD 2>/dev/null | cut -c1-12)
    echo "--- $b (merge-base $mb) ---"
    git diff --stat "$mb" "origin/$b" 2>/dev/null | tail -3
  fi
done
