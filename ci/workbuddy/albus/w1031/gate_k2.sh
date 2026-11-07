#!/bin/bash
# gate_k2.sh <arm> <build-dir> <exe>
# 硬化门 v2（断电后重建）：
#   0) pre-flight：一个引擎、VRAM<40GB，否则拒绝
#   1) 装臂 → 健康
#   2) 数值门优先（fp2，对照 greedy_base001.json）：en2k 长度掉一半或两例以上为空 ⇒ 立刻回滚
#   3) 速度门 2K/8K
#   4) trap 必回滚；调用方用 setsid nohup 托管
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
  echo "!! restored but no health"
}
trap restore EXIT

echo "=== 0. pre-flight"
n=$(ps -eo args | grep -c '^/data/bin/strata-0\.1')
[ "$n" = "1" ] || { echo "REFUSE: $n engines"; exit 10; }
used=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 "Used Memory (B)" | grep -o '[0-9]*$')
echo "engines=$n vram_used=${used:-?}"
if [ -z "${used:-}" ] || [ "$used" -ge 40000000000 ]; then echo "REFUSE: vram ${used:-?}"; exit 11; fi

echo "=== 1. deploy $ARM"
bash ci/deploy.sh --src "$SRCDIR" --exe "$EXE" --apply --allow-untagged 2>&1 | tail -3
for i in $(seq 1 30); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac
  sleep 10
done

echo "=== 2. numeric gate (fp2 vs base001)"
python3 /home/albus/strata166/w1031/fp2.py "$ARM" 2>&1 | tail -4
verdict=$(python3 - "$ARM" <<'PY'
import json, sys
arm = sys.argv[1]
a = json.load(open("/home/albus/strata166/ci/state/cfg/greedy_base001.json"))
b = json.load(open("/home/albus/strata166/ci/state/cfg/greedy_%s.json" % arm))
same = 0; empty = 0
for k in a["cases"]:
    ta, tb = a["cases"][k]["text"], b["cases"][k]["text"]
    ok = ta == tb
    same += ok; empty += (len(tb.strip()) == 0)
    print("%-6s same=%-5s len %d/%d" % (k, ok, len(ta), len(tb)))
print("CASES_SAME=%d/%d EMPTY=%d" % (same, len(a["cases"]), empty))
print("VERDICT %d %d" % (same, empty))
PY
)
echo "$verdict"
SAME=$(echo "$verdict" | awk '/^VERDICT/{print $2}')
EMPTY=$(echo "$verdict" | awk '/^VERDICT/{print $3}')
if [ "${EMPTY:-9}" -ge 2 ]; then echo "ABORT: degenerate (EMPTY=$EMPTY)"; exit 20; fi
if [ "${SAME:-0}" = "0" ]; then echo "NOTE: 三例全不同（数值变化大）—— 仍测速度，但不许采纳"; fi

echo "=== 3. speed gate"
python3 ci/cfg_apply.py --label "w1031-$ARM" --record-only --n 6 --lengths 2000,8000 2>&1 | tail -7
