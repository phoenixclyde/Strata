#!/bin/bash
# gate_speed.sh <arm> <build> <exe> -- pre-flight + deploy + 2K/8K + 必回滚。不做数值门（fp2 已被证明不可重复）。
set -uo pipefail
ARM=$1; SRCDIR=$2; EXE=$3
R=/home/albus/strata166/pr/strata-fork
cd "$R" || exit 3
restore() {
  echo "=== restore"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -2
  for i in $(seq 1 40); do
    h=$(curl -s -m 4 localhost:8090/health || true)
    case "$h" in *'"ok"'*) echo "restored healthy after ${i}0s"; return;; esac
    sleep 10
  done
}
trap restore EXIT

n=$(ps -eo args | grep -c '^/data/bin/strata-0\.1')
used=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 "Used Memory (B)" | grep -o '[0-9]*$')
echo "pre-flight engines=$n vram=${used:-?}"
[ "$n" = "1" ] || { echo "REFUSE engines=$n"; exit 10; }
[ -n "${used:-}" ] && [ "$used" -lt 40000000000 ] || { echo "REFUSE vram"; exit 11; }

bash ci/deploy.sh --src "$SRCDIR" --exe "$EXE" --apply --allow-untagged 2>&1 | tail -3
for i in $(seq 1 30); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac
  sleep 10
done
python3 ci/cfg_apply.py --label "w1031-$ARM" --record-only --n 6 --lengths 2000,8000 2>&1 | tail -7
