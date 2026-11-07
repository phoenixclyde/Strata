#!/bin/bash
# W811 / P138b：`--prefill` 大小 × PLE 重叠 —— 由 W810 的机理读出来的第二条路
#
# W810 已经量到：`ple` 相位 = GPU 流等 16×N 行从盘上回来，在 1.4-4.8K 上是 **12.9-15.9%**。
# 源码/文档给出的时间线是：
#   * prefill 的 16×N 行在**chunk setup 就全部 issue**（PHH 的 "chunk setup (PLE rows, the expert stream plan)"），
#     collect 发生在 layer 1 => 单个 chunk 里能藏的窗口只有 embed + layer 0（约 chunk 的 2-7%）；
#   * `ple_reader.hpp:5-14` 逐字："kept at most max_inflight deep, so **a chunk's reads can run while the
#     previous chunk computes**" => **第二个 chunk 起，PLE 可以完全藏在前一个 chunk 的计算里**。
#   * 推论：`--prefill 8192` 下，短于 8192 的提示**只有一个 chunk，PLE 全部暴露**；
#     把 chunk 调小，只有**第一个 chunk** 付钱，其余藏起来。代价是小 chunk 本身的效率损失
#     （上游 0.2.5：<16 GB 的 NVIDIA 卡改用 4096，"a cold 8K prompt is 9% slower"；1M 卡 1024 慢一倍）。
#
# 臂：C8=生产 `--prefill auto`(8192)  C4=4096  C2=2048   C8b=C8 重复（规则 X）
# 每臂：read 1500/3000/6000 × 2（同一份文本）+ 解码 3×128（chunk 也改 ring/流规划，必须查解码）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w811_chunk_$STAMP.txt
SIZES=1500,3000,6000
REPS=2
ARMS=${*:-"C8 C4 C2 C8b"}

cp "$CFG" /tmp/w811_prod.json
restore_cfg() {
  cp /tmp/w811_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W811 chunk-size x PLE overlap $STAMP sizes=$SIZES reps=$REPS arms='$ARMS'" > "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start prefill=%s env_n=%d'%(d['args'][d['args'].index('--prefill')+1] if '--prefill' in d['args'] else '?',len(d['env'])))" >> "$OUT"

setarm() {   # $1=arm
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
VAL = {"C8": "auto", "C4": "4096", "C2": "2048", "C8b": "auto"}[arm]
base = json.load(open("/tmp/w811_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_PREFILL_TIMING"] = "1"
e["STRATA_DECODE_TIMING"] = "1"
a = list(base.get("args") or [])
if "--prefill" in a:
    a[a.index("--prefill") + 1] = VAL
else:
    a += ["--prefill", VAL]
d = dict(base)
d["env"] = e
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d prefill=%s" % (len(d), len(e), VAL))
PY
}

run() {   # $1=arm
  local arm=$1
  setarm "$arm" >> "$OUT"
  local t0 t1 ok=0
  t0=$(date +%s)
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  t1=$(date +%s)
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s start_wall=$((t1 - t0))s" >> "$OUT"
  [ "$ok" = "0" ] && { echo "!! ABORT: never ready" >> "$OUT"; echo ABORT; exit 1; }
  python3 mt_read.py 8090 "$arm" "$DATA/w811_read_$arm.json" "$SIZES" "$REPS" kl_pool.json >> "$OUT" 2>&1
  if [ ! -f "$DATA/w811_read_$arm.json" ]; then echo "!! ABORT no json" >> "$OUT"; echo ABORT; exit 1; fi
  python3 -c "import json;print('  client_results=%d'%len(json.load(open('$DATA/w811_read_$arm.json'))['results']))" >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prompt [0-9]+ tokens = [0-9]+ reused" | cut -c1-150 | sed 's/^/  PL /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: host: chunk setup" | sed 's/^/  PHH /' >> "$OUT"
  python3 mt_gen.py 8090 "$arm" "$DATA/w811_gen_$arm.json" dec_corpus.json 128 3 >> "$OUT" 2>&1
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "strata decode timing" | sed 's/^/  DT /' >> "$OUT"
  echo >> "$OUT"
}

for a in $ARMS; do run "$a"; done

cp /tmp/w811_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
