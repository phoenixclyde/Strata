#!/bin/bash
# gate_ab.sh <arm> <builddir> <exe>   — deploy one arm, measure 2K/8K, always roll back.
set -uo pipefail
ARM=$1; SRC=$2; EXE=$3
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
restore() {
  echo "=== restore: rollback to strata-0.1.57-001"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -2
}
trap restore EXIT

echo "=== deploy $ARM"
bash ci/deploy.sh --src "$SRC" --exe "$EXE" --apply --allow-untagged 2>&1 | tail -3
for i in $(seq 1 30); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac
  sleep 10
done
python3 ci/cfg_apply.py --label "w1031-$ARM" --record-only --n 6 --lengths 2000,8000 2>&1 | tail -6
