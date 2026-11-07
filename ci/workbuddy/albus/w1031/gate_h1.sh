#!/bin/bash
# H1 arm: 0.9.0 with the pin's Q8_1 correction-sum semantics. Same two gates, always roll back.
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
restore() {
  echo "=== restore: rollback to strata-0.1.57-001"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -2
  curl -s -m 5 localhost:8090/health | head -c 120; echo
}
trap restore EXIT

echo "=== deploy H1"
bash ci/deploy.sh --src /home/albus/strata166/build-h1 --exe strata-0.1.57-005 --apply --allow-untagged 2>&1 | tail -4
for i in $(seq 1 30); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac
  sleep 10
done

echo "=== numeric: greedy fingerprint"
python3 /tmp/greedy_fingerprint.py h1 2>&1 | tail -3
python3 - <<'PY'
import json
a=json.load(open("/home/albus/strata166/ci/state/cfg/greedy_b11062.json"))
b=json.load(open("/home/albus/strata166/ci/state/cfg/greedy_h1.json"))
same=0
for k in a["cases"]:
    ta,tb=a["cases"][k]["text"], b["cases"][k]["text"]
    print("%-8s same=%-5s len %d/%d" % (k, ta==tb, len(ta), len(tb)))
    same+=ta==tb
print("CASES_SAME=%d/%d" % (same,len(a["cases"])))
PY

echo "=== speed (record-only, n=6, 2K/8K)"
python3 ci/cfg_apply.py --label w1031-h1 --record-only --n 6 --lengths 2000,8000 2>&1 | tail -8
