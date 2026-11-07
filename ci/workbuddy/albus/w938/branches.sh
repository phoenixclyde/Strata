#!/bin/bash
set -u
cd /home/albus/strata166/pr/strata-fork || exit 1

echo "=== 1) 已结实验分支：打 archive tag（保留全部提交，不 rebase） ==="
git tag -f archive/r54-port        r54-port        -m "R54 GDN megakernel: DONE_NEG (T>=4 +12.7-16.6% but production avg T 3.63-3.7 => slower). Archived pre-rebase onto 0.2.10."
git tag -f archive/exp-R55-swizzle exp/R55-swizzle -m "R55 ds_swizzle: DONE_NEG (bitwise equal, ISA -73% bpermute, kernel +-0.4%). Archived pre-rebase onto 0.2.10."
git tag -f archive/bench-mi50-32gb-262k bench-mi50-32gb-262k -m "Community bench results on one MI50 32 GB, 262,144 context (2026-10-10). Archived."
git tag -f archive/w863-main       w863-main       -m "Scratch pointer to origin/main. Archived."
for t in archive/r54-port archive/exp-R55-swizzle archive/bench-mi50-32gb-262k archive/w863-main; do
  printf "%-34s -> %s\n" "$t" "$(git rev-parse --short $t)"
done

echo
echo "=== 2) main 快进到 origin/main（镜像上游侧，业内做法：main 不放工作） ==="
echo "before: main=$(git rev-parse --short main)  origin/main=$(git rev-parse --short origin/main)"
git branch -f main origin/main
echo "after : main=$(git rev-parse --short main)"

echo
echo "=== 3) 删除已归档分支与 worktree ==="
git worktree remove --force /home/albus/strata166/work/r54 2>&1 | head -2
git worktree remove --force /home/albus/strata166/work/r55 2>&1 | head -2
for b in r54-port exp/R55-swizzle bench-mi50-32gb-262k w863-main; do
  git branch -D "$b" 2>&1 | head -1
done

echo
echo "=== 4) 现状 ==="
git branch -vv
echo "--- worktree ---"
git worktree list
echo "--- archive tags ---"
git tag -l "archive/*"
