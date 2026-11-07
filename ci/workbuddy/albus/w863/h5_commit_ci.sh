#!/bin/bash
# [W863] Commit the CI trigger narrowing. .bak files go to w863/, never into the repo.
set -eu
cd /home/albus/strata166/pr/strata-fork

for f in .github/workflows/*.yml.w863bak; do
  [ -f "$f" ] && mv -f "$f" /home/albus/strata166/w863/kernel_bak/
done

git add .github/workflows/terminal-minimal-server.yml \
        .github/workflows/terminal-portable-monitor.yml \
        docs/DOWNSTREAM.md

git -c user.name=phoenixclyde -c user.email=phoenixclyde@users.noreply.github.com \
  commit -q -m @'ci: narrow the two push-triggered workflows

Only main / gfx906/mi50 / ci/** run on push; pull_request stays main-only;
workflow_dispatch is unchanged.  paths: is untouched (4-line conflict at worst on a
rebase).  Adding branches: also stops tag pushes -- mi50-0.2.9-r1 queued 50 minutes
for a runner to re-test code that was already tested.

concurrency cancels the previous run of the same ref: three pushes in a row used to
queue three 9-minute suites.

The minimal-server suite is green again on this branch (run 41288894503, 8m38s,
1298 tests) after the telemetry fix in c3574d42.
'@

git --no-pager log --oneline -3
echo "=== clean? ==="
git status --porcelain --untracked-files=all | wc -l
echo "=== push ==="
timeout 120 git push origin gfx906/mi50 2>&1 | tail -2
