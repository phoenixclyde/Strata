#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
cd $S

for c in 058f6532 e1b27d54 285fa48b 9a352550; do
  echo "############ $c ############"
  git log -1 --format="%s%n%n%b" $c 2>/dev/null | head -8
  echo "--- 改动文件 ---"
  git show --stat --format="" $c 2>/dev/null | head -8
  echo "--- 是否只在 split 路径 ---"
  git show $c 2>/dev/null | grep -E "^\+\+\+|^ [-+].*(split|SPLIT|FNX_)" | head -8
  echo
done

echo "############ 关键词：arena / hugepage / file cache / resident ############"
git log --format="%h %ad %s" --date=short HEAD..upstream/main --grep="hugepage\|arena\|file cache\|resident" -i 2>/dev/null | cut -c1-150 | head -14

echo
echo "############ 关键词：mlock / memlock / PLE ############"
git log --format="%h %ad %s" --date=short HEAD..upstream/main --grep="mlock\|memlock" -i 2>/dev/null | cut -c1-150
