#!/bin/bash
# S1 (tile_spec) against the two gates that matter, then always roll back.
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
restore() {
  echo "=== restore: rollback to 001"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -2
}
trap restore EXIT

echo "=== deploy S1"
bash ci/deploy.sh --src /home/albus/strata166/build-lcpp --exe strata-0.1.57-003 --apply 2>&1 | tail -4
for i in $(seq 1 12); do h=$(curl -s -m 3 localhost:8090/health || true); case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac; sleep 10; done

echo "=== gate 1: greedy fingerprint (48 tokens, must match b11062 byte for byte)"
python3 /tmp/greedy_fingerprint.py s1_6501 2>&1 | tail -4
python3 - <<'PY'
import json
a=json.load(open("/home/albus/strata166/ci/state/cfg/greedy_b11062.json"))
b=json.load(open("/home/albus/strata166/ci/state/cfg/greedy_s1_6501.json"))
for k in a["cases"]:
    ta,tb=a["cases"][k]["text"], b["cases"][k]["text"]
    print("%-6s same=%-5s len %d/%d" % (k, ta==tb, len(ta), len(tb)))
    if ta!=tb:
        i=0
        while i<min(len(ta),len(tb)) and ta[i]==tb[i]: i+=1
        print("   first diff at",i,"| old",repr(ta[max(0,i-20):i+40]),"| new",repr(tb[max(0,i-20):i+40]))
PY

echo "=== gate 2: prefill @2K/@8K + decode"
python3 ci/cfg_apply.py --label w1030-s1 --record-only --n 6 --lengths 2000,8000 2>&1 | tail -7
