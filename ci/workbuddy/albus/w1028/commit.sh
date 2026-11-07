#!/bin/bash
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R"
cat > /tmp/m28.txt <<'MSG'
ci: the gate now lives where the push lands, and it caught two real defects on day one (W1028)

GitHub Actions on this fork answer 422 "Actions has been disabled for this repository" to every
dispatch, and /repos/.../actions/permissions reports enabled=true anyway -- so the API cannot be
trusted to say whether CI runs, and nothing has run since #44.  Industry answer: put the gate at
the integration point instead of in the pusher's shell.  /home/albus/strata166/gate/strata-gate.git
is a bare repo whose pre-receive hook unpacks each pushed commit into a temp dir and runs
ci/round_gate.py --ci there.  A green run writes receipts/<sha>.json; ci/deploy.sh step 0 refuses
to deploy a HEAD without one.

Proven both ways, on the receiving end only:
  git push gate gfx906/mi50                        -> GATE PASS, receipt written
  git push --no-verify gate HEAD:tmp/gate-negative -> pre-receive hook declined (BUNDLE.tsv with
                                                      phase_ms 400 instead of 510)

Two defects the first two pushes found, both of the "works where I ran it" family:

1. receive-pack exports GIT_DIR and the quarantine variables, and `git -C <dir>` does NOT
   override them.  The hook's own gate therefore talked to the bare repo instead of the temp
   checkout: `git describe --tags` said "No names found" and a good commit was rejected.  Fixed
   by reading the tree with an explicit --git-dir and running the gate under `env -u GIT_*`.

2. Worse, and pre-existing: ci/selftest_pin.py builds throwaway repos with `git init`, and when
   it ran inside a git hook the exported GIT_DIR made that init re-initialise the REAL worktree.
   It set `core.bare = true` on /home/albus/strata166/pr/strata-fork; every git command then
   failed with "this operation must be run in a work tree" until it was reset.  sh() now strips
   GIT_* and fixture() asserts the temp dir really is a work tree, so this cannot be silent again.

This is the same shape as W1018 (evidence only on my laptop) and W1027 (Actions off, nobody
noticed): the gate has to be somewhere the change cannot avoid.
MSG
git add ci/gate_receipt.py ci/deploy.sh ci/hooks/pre-push ci/selftest_pin.py
git -c user.name=albus -c user.email=a@b commit -q -F /tmp/m28.txt
echo "commit=$(git rev-parse --short HEAD) rc=$?"
git tag -a mi50-0.2.11-r33-10 -m "gate at the receiving end: pre-receive hook + deploy receipt" HEAD
echo "=== push gate (server-side gate):"
git push gate gfx906/mi50 2>&1 | tail -8
echo "gate_rc=${PIPESTATUS[0]}"
echo "=== receipt:"; python3 ci/gate_receipt.py
echo "=== deploy dry run (step 0 must pass):"
bash ci/deploy.sh --src /home/albus/strata166/build-r28 --exe strata-0.1.57-001 2>&1 | head -8
