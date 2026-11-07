#!/bin/bash
# [W863] Counter-proof: the same test on the SAME tree, with only telemetry.py swapped.
# fixed -> ok ; .w863bak (the version we shipped) -> FAIL. One variable.
set -u
cd /home/albus/strata166/pr/strata-fork || exit 1
T=serve/telemetry.py
IMG=strata-gfx906:0.2.9-101

run() {
  docker run --rm --entrypoint python3 -v /home/albus/strata166/pr/strata-fork:/src -w /src \
    "$IMG" -m unittest discover -s serve -p 'test_responses.py' -k NoLeakedSampler 2>&1 \
    | grep -aE '^(OK|FAILED|Ran |FAIL:|AssertionError)' | head -5
}

cp -f "$T" /tmp/telemetry_fixed.py
trap 'cp -f /tmp/telemetry_fixed.py "'"$PWD/$T"'"; rm -f /tmp/telemetry_fixed.py' EXIT

echo "=== ARM A: fixed (keeps self._thread) ==="
run

echo
echo "=== ARM B: .w863bak (anonymous thread, what CI ran) ==="
cp -f "$T.w863bak" "$T"
run

echo
echo "=== restored ==="
cp -f /tmp/telemetry_fixed.py "$T"
grep -c 'self._thread = threading.Thread' "$T"
