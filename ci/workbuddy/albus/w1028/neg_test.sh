#!/bin/bash
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
G=/home/albus/strata166/gate/strata-gate.git
cd "$R"
git worktree remove --force /tmp/wt-neg 2>/dev/null
git worktree add -f -b tmp/gate-negative /tmp/wt-neg gfx906/mi50 >/dev/null 2>&1 || { echo WORKTREE_FAIL; exit 4; }
cd /tmp/wt-neg
# break the bundle budget: a phase_ms that no longer matches PREFILL_PHASES.tsv
python3 - <<'PY'
import io
p = "ci/bundle_budget/BUNDLE.tsv"
s = io.open(p, encoding="utf-8").read()
s2 = s.replace("\t510\t", "\t400\t", 1)
assert s2 != s, "no 510 field to corrupt"
io.open(p, "w", encoding="utf-8", newline="\n").write(s2)
print("corrupted BUNDLE.tsv")
PY
git -c user.name=t -c user.email=t@t commit -qam "negative test: bundle share no longer derivable"
echo "tip=$(git rev-parse --short HEAD)"
echo "=== push to gate (must be REJECTED):"
git push --no-verify gate HEAD:refs/heads/tmp/gate-negative 2>&1 | tail -8
echo "rc=${PIPESTATUS[0]}"
cd "$R"; git worktree remove --force /tmp/wt-neg 2>/dev/null
git branch -D tmp/gate-negative >/dev/null 2>&1
echo "=== gate repo branches (should NOT contain tmp/gate-negative):"
git --git-dir="$G" for-each-ref --format="%(refname:short)" refs/heads | head
echo "dirty=$(git -C "$R" status --porcelain | wc -l)"
