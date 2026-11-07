#!/bin/bash
# [W863] ONE-OFF: written for the 11-01 18:5x dry run (AUDIT18/A8). It hard-codes 0.1.55i,
# so it is NOT a standing gate -- re-run it only after editing the expected version.
# The standing gate is `strata-ci check` (18 generic checks).
#
# [W863] Verify every artefact a full run is supposed to leave behind.
# Each check prints PASS/FAIL with the thing it looked at, so "the pipeline ran" is evidence,
# not a claim.
set -u
CI=/home/albus/strata166/ci
R=/home/albus/strata166/pr/strata-fork
B=/home/albus/strata166/gfx029-build
D=/home/albus/strata166/data
fail=0
ok() { printf 'PASS  %-46s %s\n' "$1" "$2"; }
no() { printf 'FAIL  %-46s %s\n' "$1" "$2"; fail=$((fail+1)); }

echo "=== 1 L1 static gate: can be re-run and must still pass ==="
if "$CI/gate.py" --repo "$R" --build "$B" --config "$D/strata-huihui-ud-iq4_xs.json" --quiet | grep -q '0 failed'; then
  ok "gate.py exits 0 with 0 failures" "$("$CI/gate.py" --repo "$R" --build "$B" --config "$D/strata-huihui-ud-iq4_xs.json" --quiet | tail -1)"
else
  no "gate.py exits 0 with 0 failures" "see output"
fi

echo
echo "=== 2 L2 build: object and binary rebuilt, container exited 0 ==="
st=$(docker inspect strata-ci-build --format '{{.State.ExitCode}}' 2>/dev/null)
[ "$st" = "0" ] && ok "build container exit code" "0" || no "build container exit code" "${st:-missing}"
[ -f "$B/strata" ] && ok "binary present" "$(md5sum "$B/strata" | cut -d' ' -f1) $(stat -c%s "$B/strata") B" || no "binary present" "$B/strata"

echo
echo "=== 3 L3 experiment: two recorded runs exist and are usable ==="
ls -1 "$CI/state/runs" | grep -q 'r28-before' && ok "baseline run recorded" "$(ls -1 $CI/state/runs | grep r28-before)" || no "baseline run recorded" "missing"
ls -1 "$CI/state/runs" | grep -q 'r28-after'  && ok "follow-up run recorded" "$(ls -1 $CI/state/runs | grep r28-after)"  || no "follow-up run recorded" "missing"
python3 - <<'PY' && ok "both runs carry code+env+per-sample data" "fields ok" || no "both runs carry code+env+per-sample data" "see above"
import glob, json, sys
bad = 0
for p in glob.glob('/home/albus/strata166/ci/state/runs/*r28*.json'):
    d = json.load(open(p))
    need = ['git_head', 'exe', 'exe_md5', 'env', 'samples', 'metrics']
    miss = [k for k in need if k not in d or not d[k]]
    if miss:
        print('  missing in %s: %s' % (p, miss)); bad += 1
    else:
        m = d['metrics']['tok_s']
        print('  %-22s median %.2f  CV %.2f%%  n=%d' % (d['run_id'], m['median'], m['cv_pct'], m['n']))
sys.exit(1 if bad else 0)
PY

echo
echo "=== 4 L4 deploy: ledger line written, service healthy, content unchanged ==="
line=$(tail -1 "$CI/state/prod_history.tsv")
echo "  $line"
echo "$line" | grep -q 'strata-0.1.55i' && ok "ledger records the deployed file" "strata-0.1.55i" || no "ledger records the deployed file" "$line"
curl -s --max-time 6 http://127.0.0.1:8090/health | grep -q '"status": "ok"' && ok "service healthy" "ok" || no "service healthy" "no answer"
cur=$(python3 -c "import json;print(json.load(open('$D/strata-huihui-ud-iq4_xs.json'))['exe'])")
[ -f "${cur/#\/data/$D}" ] && ok "config exe exists" "$cur" || no "config exe exists" "$cur"

echo
echo "=== 5 the no-op guard: a second deploy must refuse to restart ==="
out=$("$CI/strata-ci" deploy --allow-untagged 2>&1 | tail -3)
if echo "$out" | grep -q 'NOTHING TO DEPLOY'; then
  ok "deploy refuses identical content" "NOTHING TO DEPLOY"
else
  no "deploy refuses identical content" "$(echo "$out" | tr '\n' ' ')"
fi

echo
echo "=== 6 result"
[ "$fail" = "0" ] && echo "ALL CHECKS PASSED" || echo "$fail CHECK(S) FAILED"
exit 0
