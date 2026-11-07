#!/bin/bash
# gate_k.sh <arm> <build-dir> <exe>
# 硬化过的实验门（W1031 事故后）：
#   0) pre-flight：只允许一个引擎持卡、VRAM < 40 GB，否则拒绝安装
#   1) 装臂 → 等健康
#   2) **数值门优先**：48-token 贪心指纹；en2k 不同或三例全空 ⇒ 立刻回滚，不跑速度
#   3) 速度门：cfg_apply --record-only 2K/8K
#   4) 无论怎么退出都回滚到 001（脚本自带 trap；调用方也用 setsid nohup 托管，ssh 断了也继续）
set -uo pipefail
ARM=$1; SRCDIR=$2; EXE=$3
R=/home/albus/strata166/pr/strata-fork
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
cd "$R" || exit 3

restore() {
  echo "=== restore: rollback to strata-0.1.57-001"
  bash ci/rollback.sh --exe strata-0.1.57-001 --apply 2>&1 | tail -3
  for i in $(seq 1 40); do
    h=$(curl -s -m 4 localhost:8090/health || true)
    case "$h" in *'"ok"'*) echo "restored healthy after ${i}0s"; return;; esac
    sleep 10
  done
  echo "!! restored but health did not come back"
}
trap restore EXIT

echo "=== 0. pre-flight"
n=$(ps -eo args | grep -c '^/data/bin/strata-0\.1')
[ "$n" = "1" ] || { echo "REFUSE: $n engine processes are running"; exit 10; }
used=$(rocm-smi --showmeminfo vram 2>/dev/null | grep -m1 "Used Memory (B)" | grep -o '[0-9]*$')
echo "engines=$n vram_used=${used:-?}"
[ -n "${used:-}" ] && [ "$used" -lt 40000000000 ] || { echo "REFUSE: vram used ${used:-unknown} >= 40 GB"; exit 11; }

echo "=== 1. deploy $ARM ($EXE)"
bash ci/deploy.sh --src "$SRCDIR" --exe "$EXE" --apply --allow-untagged 2>&1 | tail -3
for i in $(seq 1 30); do
  h=$(curl -s -m 3 localhost:8090/health || true)
  case "$h" in *'"ok"'*) echo "healthy after ${i}0s"; break;; esac
  sleep 10
done

echo "=== 2. numeric gate first"
python3 /tmp/greedy_fingerprint.py "$ARM" 2>&1 | tail -3
python3 - "$ARM" <<'PY'
import json, sys
arm = sys.argv[1]
a = json.load(open("/home/albus/strata166/ci/state/cfg/greedy_b11062.json"))
b = json.load(open("/home/albus/strata166/ci/state/cfg/greedy_%s.json" % arm))
same = 0; empty = 0
for k in a["cases"]:
    ta, tb = a["cases"][k]["text"], b["cases"][k]["text"]
    print("%-8s same=%-5s len %d/%d" % (k, ta == tb, len(ta), len(tb)))
    same += ta == tb
    empty += (len(tb.strip()) == 0)
print("CASES_SAME=%d/%d EMPTY=%d" % (same, len(a["cases"]), empty))
open("/tmp/%s.verdict" % arm, "w").write("%d %d" % (same, empty))
PY
read -r SAME EMPTY < /tmp/$ARM.verdict
if [ "$EMPTY" -ge 2 ]; then echo "ABORT: degenerate answers (EMPTY=$EMPTY) -- 不算速度，直接回滚"; exit 20; fi

echo "=== 3. speed gate (2K/8K)"
python3 ci/cfg_apply.py --label "w1031-$ARM" --record-only --n 6 --lengths 2000,8000 2>&1 | tail -7
echo "=== 4. done (rollback in trap)"
