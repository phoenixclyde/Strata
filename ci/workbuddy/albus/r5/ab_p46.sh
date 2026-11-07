#!/bin/bash
# W816：**这个构建的贪心答案到底为什么不可复现** —— 找到它，比 P138 的得失重要
#
# 已知（W814）：生产 vs 生产，两次启动、同输入，6 个样本 6 个 sha256，连长度都不同。
# 上游 0.2.5 发布说明把这类现象归为「按时钟猜提示路径」（旧版本改答案）。
# 本车要回答的是**可操作的那个问题**：变的是「同一个实例内」还是「跨重启」？
#   · 实例内也不稳 => 是 kernel/专家的非确定性（pool 调度、atomic 归约），与启动无关；
#   · 实例内稳、跨重启变 => 是启动期选定的东西（auto chunk / 借槽 / ring）在变。
# 仪器：`STRATA_TRACE=1` —— 每个请求会印 `trace: lent N slots for M tokens ...`，
#       **M 就是这一块实际用的 chunk**，直接可读；配合 `prefill timing: N tokens` 交叉核对。
# 臂：B1 B2（两次启动，各自连发 3 次同一个 prompt）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
OUT=$DATA/w816_det_$(date +%Y%m%d_%H%M%S).txt
ARMS=${*:-"B1 B2"}

cp "$CFG" /tmp/w816_prod.json
DONE=0
restore() {
  [ "$DONE" = "1" ] && return 0
  DONE=1
  cp /tmp/w816_prod.json "$CFG"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored" >> "$OUT"
}
trap restore EXIT

echo "# W816 determinism probe $(date +%F' '%T) arms='$ARMS'" > "$OUT"
python3 - "$CFG" <<'PY' >> "$OUT"
import json
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open("/tmp/w816_prod.json"))
e = dict(d.get("env") or {})
e["STRATA_TRACE"] = "1"
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK env_n=%d trace=%s" % (len(e), e.get("STRATA_TRACE")))
PY

for A in $ARMS; do
  ok=0
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $A ready=${ok}s" >> "$OUT"
  [ "$ok" = "0" ] && { echo "!! ABORT never ready" >> "$OUT"; echo ABORT; exit 1; }
  # 两次「暖身」请求（第一次带冷启动效应，不参与判据）
  python3 mt_det.py 8090 "$A-warm" dec_corpus.json 0 2 32 >> "$OUT" 2>&1
  python3 mt_det.py 8090 "$A" dec_corpus.json 0 3 64 >> "$OUT" 2>&1
  # 这一臂的 chunk / 借槽（真值）
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "strata trace: lent|strata trace: prompt start|strata trace: read [0-9]+ tokens" \
    | tail -24 | cut -c1-140 | sed 's/^/  TR /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | cut -c1-90 | sed 's/^/  PH /' >> "$OUT"
  python3 -c "import json;d=json.load(open('$CFG'));print('  ENG env_n=%d'%len(d['env']))" >> "$OUT"
done

DONE=1
cp /tmp/w816_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
