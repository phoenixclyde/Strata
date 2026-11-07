#!/bin/bash
# W863 · git 收尾三件事（都有备份/回退点，失败即停）
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1

echo "########## 1. gfx906-build-fixes-402: 本地 3 个陈旧提交 -> 留备份引用后归零 ##########"
echo "--- those 3 commits (subjects) ---"
git log --oneline origin/gfx906-build-fixes-402..gfx906-build-fixes-402
echo "--- are they the same work as the three dedicated branches? ---"
for pair in "amd-monitor-pcie-link:5241c728" "gfx906-cpu-share-guard:eac9cef5" "web-sparkline-axis-floor:48cd120d"; do
  br=${pair%%:*}; sha=${pair##*:}
  echo -n "  $br has that subject? "
  git log --format='%s' -1 "$sha" | cut -c1-60
done
# 备份成 tag，再 reset（零丢失）
git tag -f archive/gfx906-build-fixes-402-local 468bdeeb >/dev/null 2>&1 && echo "backup tag -> archive/gfx906-build-fixes-402-local"
git branch -f gfx906-build-fixes-402 origin/gfx906-build-fixes-402
echo -n "after: "; git rev-list --left-right --count gfx906-build-fixes-402...origin/gfx906-build-fixes-402

echo
echo "########## 2. 树里的 3 个 .cu.* 备份文件 -> 移到仓库外（保留回滚用）##########"
BAK=/home/albus/strata166/w863/kernel_bak
mkdir -p "$BAK"
for f in src/kernels/cuda/native_mmvq.cu.w862bak src/kernels/cuda/native_mmvq.cu.w863bak src/kernels/cuda/native_mmvq.cu.w863bak2; do
  if [ -f "$f" ]; then mv -f "$f" "$BAK/"; echo "  moved $f -> $BAK/"; fi
done
ls -l "$BAK" | tail -4
echo -n "git status now: "; git status --porcelain | wc -l

echo
echo "########## 3. 让 main 成为主线的祖先（main ⊂ gfx906/0.2.9-mi50）##########"
git tag -f archive/pre-main-merge-78fa2a72 78fa2a72 >/dev/null 2>&1 && echo "backup tag -> archive/pre-main-merge-78fa2a72"
git checkout gfx906/0.2.9-mi50 >/dev/null 2>&1
echo "replay the 2 commits onto main (base c62d5e3a):"
git rebase --onto main c62d5e3a gfx906/0.2.9-mi50 2>&1 | tail -5
if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
  echo "REBASE CONFLICT -> abort, keep 78fa2a72"
  git rebase --abort
  git checkout -B gfx906/0.2.9-mi50 archive/pre-main-merge-78fa2a72 >/dev/null 2>&1
  exit 2
fi
echo "--- new tip ---"
git log --oneline -4
echo -n "main is ancestor of mi50? "; git merge-base --is-ancestor main HEAD && echo YES || echo NO
echo -n "mi50 ahead of main: "; git rev-list --count main..HEAD
echo -n "mi50 behind main: ";  git rev-list --count HEAD..main

echo
echo "########## 4. push the main line (fork only) ##########"
timeout 180 git push --force-with-lease=gfx906/0.2.9-mi50:78fa2a72 origin gfx906/0.2.9-mi50 2>&1 | tail -3
echo
echo "=== final state ==="
git rev-parse --abbrev-ref HEAD; git log --oneline -1
git status --porcelain
git ls-remote --heads origin gfx906/0.2.9-mi50 main
