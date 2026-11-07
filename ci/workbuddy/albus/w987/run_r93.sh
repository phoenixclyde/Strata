#!/bin/bash
set -u
cd /home/albus/strata166/pr/strata-fork
echo "===== 基线（重启后，多长度）====="
python3 ci/cfg_apply.py --label w987-base --record-only --restart-baseline --n 6 --lengths 2000,8000,16000 2>&1 | tail -10

echo
echo "===== 臂：--prefill 8192 ====="
python3 ci/cfg_apply.py --label w987-prefill8192 --set prefill=8192 --baseline w987-base --n 6 --lengths 2000,8000,16000 --apply 2>&1 | tail -14
