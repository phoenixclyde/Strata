#!/bin/bash
# W863 · 分支全量审计：本地 / origin / upstream 三方 + 谁落后谁领先 + 最后提交时间
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== repo facts ==="
echo -n "shallow: "; git rev-parse --is-shallow-repository
echo -n ".git size: "; du -sh .git 2>/dev/null | cut -f1
echo -n "HEAD: "; git rev-parse --abbrev-ref HEAD; git rev-parse --short HEAD
echo -n "untracked in tree: "; git status --porcelain | grep -c '^??'
echo
echo "=== all refs: local | origin | upstream ==="
printf "%-34s %-10s %-10s %-10s\n" BRANCH LOCAL ORIGIN UPSTREAM
for b in $(git for-each-ref --format='%(refname:short)' refs/heads refs/remotes/origin refs/remotes/upstream | sed 's#^origin/##;s#^upstream/##' | sort -u); do
  L=$(git rev-parse --short "refs/heads/$b" 2>/dev/null || echo -)
  O=$(git rev-parse --short "refs/remotes/origin/$b" 2>/dev/null || echo -)
  U=$(git rev-parse --short "refs/remotes/upstream/$b" 2>/dev/null || echo -)
  printf "%-34s %-10s %-10s %-10s\n" "$b" "$L" "$O" "$U"
done
echo
echo "=== divergence (local vs origin) ==="
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  if git rev-parse --verify -q "refs/remotes/origin/$b" >/dev/null; then
    S=$(git rev-list --left-right --count "$b...origin/$b")
    A=${S%%	*}; B=${S##*	}
    [ "$A" != "0" ] || [ "$B" != "0" ] && echo "  $b: ahead $A / behind $B"
  else
    echo "  $b: NOT on origin"
  fi
done
echo "  (只有上面列出来的不一致；没列出的都是 0/0)"
echo
echo "=== last commit date per branch (origin) ==="
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -v 'origin$'); do
  d=$(git log -1 --format='%ci' "$b")
  s=$(git log -1 --format='%s' "$b" | cut -c1-56)
  printf "  %-34s %s  %s\n" "${b#origin/}" "${d:0:16}" "$s"
done
echo
echo "=== upstream ==="
git log -1 --format='  upstream/main %h %ci %s' upstream/main | cut -c1-120
echo -n "  tag v0.2.9 -> "; git rev-parse --short 'v0.2.9^{commit}'
echo
echo "=== who is the base of the MI50 line ==="
echo -n "  merge-base(origin/gfx906/0.2.9-mi50, upstream/main) = "
git merge-base origin/gfx906/0.2.9-mi50 upstream/main | cut -c1-12
