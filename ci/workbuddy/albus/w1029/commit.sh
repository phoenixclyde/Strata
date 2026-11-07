#!/bin/bash
set -uo pipefail
cd /home/albus/strata166/pr/strata-fork || exit 3
cat > /tmp/m29.txt <<'MSG'
ci: the red was a hardcoded path, and the gate is GitHub's again (W1029)

Runs #42-#44 failed in 9-11 seconds each.  The log says why, in one line:

  ROUND_GATE: FAIL (1)
    - selftest_pin.py: [BAD] baseline: both declarations agree   rc=2

rc=2 is Python refusing to open a file.  selftest_pin.py had
  RC = "/home/albus/strata166/pr/strata-fork/ci/release_check.py"
-- an absolute path to *my* work repo, which does not exist on a runner.  Every case then
reported a pin failure that had nothing to do with the pin, and the one case that must pass
(baseline) could not.  Now RC is resolved next to __file__, and a missing file raises a clear
SystemExit instead of being scored as "[BAD]".  Proof: a depth-1 clone of this branch -- no work
repo, no tags, exactly what a runner has -- runs `ci/round_gate.py --ci` to PASS, SELFTEST 4/4.

Also in this change:

  * .github/workflows/downstream-gate.yml: checkout with fetch-depth 0 + fetch-tags.  A depth-1
    checkout has no tags and every tag-based check fails for a reason unrelated to the change.
  * ci/gh_gate.py: the deploy gate is GitHub's run now.  `ci/deploy.sh` step 0 asks for a
    completed, successful `downstream-gate` run for the exact HEAD sha; exit 6 = no run / still
    running, 7 = failed (URL printed), 8 = API.  The W1028 local receipt stays, as a note.

One blocker is not in the code: this repository's own Actions switch is off.
  GET  /repos/.../actions/permissions  -> {"enabled": true, "allowed_actions": "all"}
  PUT  same endpoint                   -> 204
  POST .../downstream-gate.yml/dispatches -> 422 "Actions has been disabled for this repository"
  same call on phoenixclyde/vllm-gfx906-routeb (not a fork) -> 422 "does not have workflow_dispatch
  trigger", i.e. Actions answers normally there, so it is this repo, not the account.
No API flips that switch; the Actions tab's banner (or Settings -> Actions -> General) does.
Until then gh_gate.py exits 6 and deploys are refused -- which is the point: a gate that can be
skipped when the cloud is inconvenient is not a gate.
MSG
git add ci/gh_gate.py ci/deploy.sh ci/selftest_pin.py .github/workflows/downstream-gate.yml
git -c user.name=albus -c user.email=a@b commit -q -F /tmp/m29.txt
echo "commit=$(git rev-parse --short HEAD)"
git tag -a mi50-0.2.11-r33-11 -m "CI red root cause (hardcoded path) + GitHub run as the deploy gate" HEAD
git push gate gfx906/mi50 2>&1 | tail -4
echo "gate_rc=${PIPESTATUS[0]}"
git push origin gfx906/mi50 mi50-0.2.11-r33-11 2>&1 | tail -3
echo "=== 30s 后查 GitHub 是否起 run:"
sleep 30
python3 ci/gh_gate.py; echo "gh_gate rc=$?"
