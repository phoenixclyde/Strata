#!/bin/bash
set -u
S=~/strata166/pr/strata-fork
cd $S
R="HEAD..upstream/main"

echo "########## A. 排除 split / 新架构 / 非 Linux 平台后的通用提交 ##########"
git log --format="%h %ad %s" --date=short $R 2>/dev/null \
 | grep -viE "split|FNX_|dflash|df2|RCCL|peer push|all-cards" \
 | grep -viE "gfx1[0-9]{3}|gfx1201|gfx1151|gfx1100|gfx1101|gfx1102|gfx1030|gfx1031|gfx1010|gfx1011" \
 | grep -viE "windows|win32|metal|macos|sycl|arc|rdna|rx ?[0-9]{4}|r9700|a6000|rtx|nvidia|sm_[0-9]|blackwell|ada" \
 | grep -viE "app:|App |terminal|setup|installer|ui |screenshot|docs?:|readme|changelog" \
 | cut -c1-140 | head -60

echo
echo "########## B. 其中「正确性 / 健壮性」类 ##########"
git log --format="%h %s" --date=short $R 2>/dev/null \
 | grep -viE "split|FNX_|dflash|df2|RCCL|gfx1[0-9]{3}|windows|metal|sycl|app:|terminal|setup" \
 | grep -iE "fatal|crash|hang|deadlock|corrupt|overflow|regression|wrong|incorrect|NaN|leak|race|stale|never|silently" \
 | cut -c1-140 | head -30

echo
echo "########## C. 我们树里有没有 serve/server.py（cherry-pick 要一起改） ##########"
ls -l serve/server.py 2>/dev/null | awk '{print "  ", $5, $6, $7, $8}'
echo -n "  上游版本行数: "; git show upstream/main:serve/server.py 2>/dev/null | wc -l
echo -n "  我们版本行数: "; wc -l < serve/server.py 2>/dev/null

echo
echo "########## D. 实测 e1b27d54 的 cherry-pick 冲突 ##########"
rm -rf /tmp/w934 && git worktree add -f /tmp/w934 HEAD >/dev/null 2>&1
cd /tmp/w934
git cherry-pick -n e1b27d54 >/tmp/cp934.log 2>&1
rc=$?
echo "  rc=$rc"
grep -cE "^CONFLICT|^error" /tmp/cp934.log 2>/dev/null | sed 's/^/  冲突行数: /'
grep -E "^CONFLICT|^error" /tmp/cp934.log 2>/dev/null | head -6
git cherry-pick --abort 2>/dev/null; git reset --hard -q HEAD
cd $S && git worktree remove --force /tmp/w934 2>/dev/null
echo "  worktree cleaned"
