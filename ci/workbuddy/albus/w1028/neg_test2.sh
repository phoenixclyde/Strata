#!/bin/bash
set -u
R=/home/albus/strata166/pr/strata-fork
G=/home/albus/strata166/gate/strata-gate.git
cd "$R"
git --git-dir="$G" update-ref -d refs/heads/tmp/gate-negative 2>/dev/null
git worktree remove --force /tmp/wt-neg2 2>/dev/null
rm -rf /tmp/wt-neg2
git branch -D tmp/gate-negative 2>/dev/null
git worktree add -f -b tmp/gate-negative /tmp/wt-neg2 gfx906/mi50 || { echo WT_FAIL; exit 4; }
cd /tmp/wt-neg2 || exit 4
echo "wt head before=$(git rev-parse --short HEAD)"
python3 - <<'PY'
import io
p = "ci/bundle_budget/BUNDLE.tsv"
s = io.open(p, encoding="utf-8").read()
s2 = s.replace("\t510\t", "\t400\t", 1)
assert s2 != s
io.open(p, "w", encoding="utf-8", newline="\n").write(s2)
print("corrupted")
PY
git -c user.name=t -c user.email=t@t commit -qan -m "negative test: bundle share no longer derivable"
echo "commit rc=$?  head now=$(git rev-parse --short HEAD)"
git show --stat --oneline HEAD | head -3
echo "=== push --no-verify to gate (server must reject on its own):"
git push --no-verify gate HEAD:refs/heads/tmp/gate-negative 2>&1 | tail -8
echo "push rc=${PIPESTATUS[0]}"
echo "=== gate branches:"; git --git-dir="$G" for-each-ref --format="%(refname:short)" refs/heads
cd "$R"; git worktree remove --force /tmp/wt-neg2 2>/dev/null; rm -rf /tmp/wt-neg2
git branch -D tmp/gate-negative 2>/dev/null
echo "main dirty=$(git -C "$R" status --porcelain | wc -l)"
