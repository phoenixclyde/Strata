#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
cd $S

echo "########## A. 远端配置 ##########"
git remote -v

echo
echo "########## B. 强制刷新上游（https 代理） ##########"
timeout 180 git fetch --force --tags upstream 2>&1 | tail -8
echo "RC=$?"

echo
echo "########## C. 本地 ref 当前指向 ##########"
printf "%-16s %s\n" "upstream/main" "$(git log -1 --format='%h %ad %s' --date=short upstream/main 2>/dev/null | cut -c1-90)"
printf "%-16s %s\n" "HEAD" "$(git log -1 --format='%h %ad %s' --date=short HEAD | cut -c1-90)"

echo
echo "########## D. 远端真实 HEAD（ls-remote，绕过本地 ref） ##########"
timeout 90 git ls-remote upstream HEAD refs/heads/main 2>&1 | head -3

echo
echo "########## E. 最新 tag ##########"
git tag --sort=-creatordate | head -6
echo "--- 各 tag 指向 ---"
for t in $(git tag --sort=-creatordate | head -4); do
  printf "  %-10s %s\n" "$t" "$(git log -1 --format='%h %ad' --date=short $t 2>/dev/null)"
done

echo
echo "########## F. 真实差距（fetch 后） ##########"
echo -n "  behind/ahead (upstream/main...HEAD): "
git rev-list --left-right --count upstream/main...HEAD 2>&1
