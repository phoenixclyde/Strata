#!/bin/bash
set -u
R=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/backup
mkdir -p $B
cd $R || exit 1

echo "=== 1) 全量 bundle（所有 refs） ==="
git bundle create $B/strata-all-refs-20261104.bundle --all 2>&1 | tail -3
ls -lh $B/strata-all-refs-20261104.bundle | awk '{print $5, $9}'

echo
echo "=== 2) 备份分支（每个分支一个 pre-rebase 指针） ==="
for b in gfx906/mi50 r54-port exp/R55-swizzle bench-mi50-32gb-262k main w863-main; do
  git branch -f "pre-rebase/$(echo $b | tr '/' '-')" "$b" 2>&1 && echo "  pre-rebase/$(echo $b | tr '/' '-') -> $(git rev-parse --short $b)"
done

echo
echo "=== 3) rerere（复用冲突解） ==="
git config rerere.enabled true
git config --get rerere.enabled

echo
echo "=== 4) 记录 rebase 前状态 ==="
git rev-parse HEAD > $B/rebase-before-head.txt
git merge-base HEAD upstream/main | tee -a $B/rebase-before-head.txt

echo
echo "=== 5) 上游有没有动 third_party/ggml（我们 vendored 的） ==="
git diff --stat v0.2.9..upstream/main -- third_party/ggml | tail -5
echo "--- 改动文件数 ---"
git diff --name-only v0.2.9..upstream/main -- third_party/ggml | wc -l

echo
echo "=== 6) 上游版本与引擎号 ==="
git show upstream/main:CMakeLists.txt | grep -m1 "project(strata VERSION"
