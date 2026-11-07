#!/bin/bash
set -uo pipefail
cd /home/albus/strata166/pr/strata-fork || exit 3
git -c user.name=albus -c user.email=a@b commit -q --allow-empty -m "ci: empty commit to trigger the first run after Actions was re-enabled

GitHub does not backfill runs for commits pushed while Actions was off, so enabling the switch
has to be followed by a push.  Nothing in the tree changes."
echo "head=$(git rev-parse --short HEAD)"
git push -q gate gfx906/mi50 && echo "gate: receipt $(ls /home/albus/strata166/gate/strata-gate.git/receipts | wc -l) total"
git push -q origin gfx906/mi50 && echo "origin: pushed"
echo "=== 等 GitHub 起 run（最多 180s）:"
python3 ci/gh_gate.py --wait 180; echo "gh_gate rc=$?"
