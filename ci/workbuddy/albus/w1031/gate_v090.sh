#!/bin/bash
# W1031 / R100-S1 gates for the llama.cpp v0.9.0 (b12110) trial build.
#   1) install build-v090/strata as strata-0.1.57-004 and restart through ci/deploy.sh
#   2) numeric gate: greedy fingerprint on 3 cases, must match the b11062 baseline
#   3) speed gate: cfg_apply --record-only (2K/8K prefill + decode), n=6
#   4) ALWAYS roll back to strata-0.1.57-001
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
restore() {
  echo "=== restore: rollback to strata-0.1.57-001"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -3
  curl -s -m 5 localhost:8090/health | head -c 200; echo
}
trap restore EXIT

echo "=== 1. deploy v0.9.0 build"
bash ci/deploy.sh --src /home/albus/strata166/build-v090 --exe strata-0.1.57-004 --apply --allow-untagged 2>&1 | tail -6
for i in $(seq 1 30); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac
  sleep 10
done
curl -s -m 5 localhost:8090/health | head -c 200; echo

echo "=== 2. numeric gate (greedy fingerprint, 3 cases)"
python3 /tmp/greedy_fingerprint.py v090 2>&1 | tail -4
python3 - <<'PY'
import json
a=json.load(open("/home/albus/strata166/ci/state/cfg/greedy_b11062.json"))
b=json.load(open("/home/albus/strata166/ci/state/cfg/greedy_v090.json"))
same=0
for k in a["cases"]:
    ta,tb=a["cases"][k]["text"], b["cases"][k]["text"]
    print("%-8s same=%-5s len %d/%d" % (k, ta==tb, len(ta), len(tb)))
    if ta==tb:
        same+=1
    else:
        i=0
        while i<min(len(ta),len(tb)) and ta[i]==tb[i]: i+=1
        print("   first diff at",i,"| old",repr(ta[max(0,i-25):i+45]),"| new",repr(tb[max(0,i-25):i+45]))
print("CASES_SAME=%d/%d" % (same,len(a["cases"])))
PY

echo "=== 3. speed gate (record-only, n=6, 2K/8K)"
python3 ci/cfg_apply.py --label w1031-v090 --record-only --n 6 --lengths 2000,8000 2>&1 | tail -10
