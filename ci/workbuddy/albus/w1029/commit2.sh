#!/bin/bash
set -uo pipefail
cd /home/albus/strata166/pr/strata-fork || exit 3
cat > /tmp/m30.txt <<'MSG'
ci: the second red was a host fact scored as a release failure (W1029)

Run #45 (the first one after Actions was re-enabled) failed at the round gate with:

  - selftest_pin.py: [BAD] baseline: both declarations agree  rc=1
      [FAIL] container image  error: no such object: strata166-407

That is `docker inspect` on a runner that has docker but not our container.  The pin self-test
was judging five rows that only exist on the build box (container image, BUILD-IMAGE.json,
binary, engine versions agree, llama.cpp tree).  A host fact is not a release fact: on a runner
the honest answer is SKIP, not FAIL.

release_check.py grew `--offline`, which turns exactly those five rows into SKIP (the tag, pin and
engine-build rows are still judged -- they are what a static run can actually check), and
selftest_pin.py now calls it with `--offline`.

Verified where it matters: `ci/selftest_pin.py` is 4/4, `release_check.py --offline` is PASS with
five SKIPs named as such.  The next GitHub run is the judge.

Two leaks in two runs, both the same shape: a check that quietly assumed the machine it was
written on.  First the absolute path to release_check.py, now the container name.
MSG
git add ci/release_check.py ci/selftest_pin.py
git -c user.name=albus -c user.email=a@b commit -q -F /tmp/m30.txt
echo "head=$(git rev-parse --short HEAD)"
git tag -a mi50-0.2.11-r33-13 -m "CI: --offline for host-only release rows" HEAD
git push -q gate gfx906/mi50 && echo "gate ok"
git push -q origin gfx906/mi50 mi50-0.2.11-r33-13 && echo "origin ok"
sleep 45
python3 ci/gh_gate.py --wait 240; echo "gh_gate rc=$?"
