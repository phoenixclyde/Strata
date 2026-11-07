#!/bin/bash
# W817：不可复现的元凶是谁 —— 投机解码（`--spec 4`）还是专家缓存/CPU 池？
#
# W816 已经推到这一步：**同一个实例内、连续三次同输入，三个不同答案**（B1 3/3、B3 3/3、B2 2/3），
# 而 chunk 稳定在 `lent 191 slots for 256 tokens` ⇒ **不是启动期选路径，是每请求都在变**。
# 最可能的两个：①投机解码每个窗口的批形状不同（接受几个 draft 决定 batch 形状 -> 归约顺序变）；
#                 ②专家缓存/CPU 池的驻留集合随请求演化（同一专家有时在卡上、有时在 CPU 上算）。
# 本车只切一个变量：`--spec 0`（源码 4247 行：`o.spec < 2` 就不走 MTP 路径）。
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
OUT=$DATA/w817_spec0_$(date +%Y%m%d_%H%M%S).txt
BOOTS=${*:-"S1 S2"}

cp "$CFG" /tmp/w817_prod.json
DONE=0
restore() {
  [ "$DONE" = "1" ] && return 0
  DONE=1
  cp /tmp/w817_prod.json "$CFG"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored" >> "$OUT"
}
trap restore EXIT

echo "# W817 spec-0 determinism $(date +%F' '%T) boots='$BOOTS'" > "$OUT"
python3 - <<'PY' >> "$OUT"
import json
p = "/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json"
d = json.load(open("/tmp/w817_prod.json"))
e = dict(d.get("env") or {})
e["STRATA_TRACE"] = "1"
a = list(d.get("args") or [])
if "--spec" in a:
    a[a.index("--spec") + 1] = "0"
d["env"] = e
d["args"] = a
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK env_n=%d spec=%s" % (len(e), a[a.index("--spec") + 1]))
PY

for A in $BOOTS; do
  ok=0
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $A spec=0 ready=${ok}s" >> "$OUT"
  [ "$ok" = "0" ] && { echo "!! ABORT never ready" >> "$OUT"; echo ABORT; exit 1; }
  python3 mt_det.py 8090 "$A-warm" dec_corpus.json 0 2 32 >> "$OUT" 2>&1
  python3 mt_det.py 8090 "$A" dec_corpus.json 0 4 64 >> "$OUT" 2>&1
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "lent [0-9]+ slots|drafts accepted" | tail -8 | cut -c1-130 | sed 's/^/  TR /' >> "$OUT"
done

DONE=1
cp /tmp/w817_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
