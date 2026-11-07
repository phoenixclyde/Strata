#!/bin/bash
set -uo pipefail
G=/home/albus/strata166/gate/strata-gate.git
mkdir -p /home/albus/strata166/gate
[ -d "$G" ] || git init --bare -q "$G"
cp /tmp/gate_pre_receive.sh "$G/hooks/pre-receive"
chmod +x "$G/hooks/pre-receive"
mkdir -p "$G/receipts"
cd /home/albus/strata166/pr/strata-fork
git remote remove gate 2>/dev/null || true
git remote add gate "$G"
echo "remote:"; git remote -v | grep gate
echo "=== push through the gate (this is the enforcement point):"
git push gate gfx906/mi50 2>&1 | tail -14
echo "=== rc=$?"
echo "=== receipts:"; ls -l "$G/receipts" | tail -4
