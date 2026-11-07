#!/bin/bash
set -uo pipefail
R=/home/albus/strata166/pr/strata-fork
cd "$R"
echo "=== N1 no receipt for an older sha (expect exit 3):"
python3 ci/gate_receipt.py --sha 9104cc00 ; echo "rc=$?"
echo "=== N2 gate edited after the receipt (expect exit 4):"
cp ci/round_gate.py /tmp/rg.bak
printf '\n# drift test\n' >> ci/round_gate.py
python3 ci/gate_receipt.py; echo "rc=$?"
cp /tmp/rg.bak ci/round_gate.py
echo "=== restored:"
python3 ci/gate_receipt.py; echo "rc=$?"
echo "dirty=$(git status --porcelain | wc -l)"
echo "=== push origin (mirror) + tag:"
git push origin gfx906/mi50 mi50-0.2.11-r33-10 2>&1 | tail -4
echo "=== state: head=$(git rev-parse --short HEAD) describe=$(git describe --tags) ahead=$(git rev-list --count upstream/main..HEAD) behind=$(git rev-list --count HEAD..upstream/main)"
