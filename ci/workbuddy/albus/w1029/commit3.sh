#!/bin/bash
set -uo pipefail
cd /home/albus/strata166/pr/strata-fork || exit 3
cat > /tmp/m31.txt <<'MSG'
ci: judge the recipe when there is no image, and give the fixture one (W1029)

Run #46 got one row further and stopped at:

  [BAD] baseline ... rc=1 | [FAIL] llama.cpp pin (release) (absent)

Correct diagnosis: --offline skipped BUILD-IMAGE.json, and the release pin row then read that
same absent file.  Two fixes, both about judging the right object:

  * offline, the release pin is read from ci/docker/Dockerfile-* (the recipe that bakes the pin
    in), so the row still means something on a runner instead of being skipped or absent;
  * the self-test fixture now writes that Dockerfile too, because a fixture that lacks a file
    the check reads is not a repo -- it was "absent" for every case, including baseline.

Verified in a clean depth-1 clone with no container and no /data (what a runner is):
ROUND_GATE PASS, SELFTEST 4/4.

Three reds, three environment assumptions: an absolute path, a container name, and a fixture
that was not the shape of the thing it stood for.
MSG
git add ci/release_check.py ci/selftest_pin.py
git -c user.name=albus -c user.email=a@b commit -q -F /tmp/m31.txt
echo "head=$(git rev-parse --short HEAD)"
git tag -a mi50-0.2.11-r33-14 -m "CI: release pin from the recipe when offline; complete fixture" HEAD
git push -q gate gfx906/mi50 && echo "gate ok"
git push -q origin gfx906/mi50 mi50-0.2.11-r33-14 && echo "origin ok"
sleep 40
python3 ci/gh_gate.py --wait 200; echo "gh_gate rc=$?"
