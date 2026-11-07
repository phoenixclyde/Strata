#!/bin/bash
set -u
cd /home/albus/strata166/pr/strata-fork
echo "===== 基线（重启后）====="
python3 ci/cfg_apply.py --label p4-base3 --record-only --restart-baseline --n 5 2>&1 | tail -4
echo
echo "===== 0.35（对照 p4-base3）====="
python3 ci/cfg_apply.py --label p4d2b-pciefrac035 --set pcie-frac=0.35 --baseline p4-base3 --n 5 --apply 2>&1 | tail -7
echo
echo "===== 0.10（对照 p4-base3）====="
python3 ci/cfg_apply.py --label p4d3b-pciefrac010 --set pcie-frac=0.10 --baseline p4-base3 --n 5 --apply 2>&1 | tail -7
