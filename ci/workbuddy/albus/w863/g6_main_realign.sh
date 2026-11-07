#!/bin/bash
# W863 · main 对齐：不 rebase（本地是 grafted 浅克隆，历史不完整），改为
#   main := upstream/main (c62d5e3a) + cherry-pick 我们那个 docs 提交
set -u
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 1
echo "=== is this a shallow / grafted clone? ==="
echo -n "shallow repo: "; git rev-parse --is-shallow-repository
wc -l < .git/shallow 2>/dev/null || echo "no .git/shallow"
echo "grafted markers:"; git log --oneline --all --graph 2>/dev/null | grep -c grafted
echo
echo "=== our docs commit is the only thing main adds ==="
git show --stat --oneline 9c369f15 | head -6
echo
echo "=== build the aligned main: c62d5e3a + that commit ==="
git checkout -B w863/main-align upstream/main 2>&1 | tail -2
git -c user.name="phoenixclyde" -c user.email="phoenixclyde@users.noreply.github.com" \
    cherry-pick 9c369f15 2>&1 | tail -4
echo
echo "=== result ==="
git log --oneline -3
ls -l docs/hipblaslt_gfx906_investigation.md 2>/dev/null | head -2
echo
echo "=== does the aligned main contain upstream v0.2.9 exactly? ==="
git rev-list --count upstream/main..w863/main-align
echo -n "behind upstream: "; git rev-list --count w863/main-align..upstream/main
