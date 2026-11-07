#!/bin/bash
# W805b：大 prompt 的 chunk 尺寸（8192 vs 16384）—— 只动一个变量
#   机理（源码逐字）：`stream_all` 时「一个 chunk 会把每个专家读一遍」，所以 **chunk 数就是成本单位**
#   （prefill.cpp:7459 注释「a prompt's cost is its number of such chunks」；
#     generate.cpp:7448 #2824 注释「a single pass reads each expert once … splitting it would only add a pass」）。
#   相位实测也同向：每 1k token 的 gate/up 在 1881/3313/6152 token 上是 456/431/351 ms => 越大越省。
#   风险：prompt 缓冲 = 160 + chunk*680/1024 MiB（generate.cpp:4451），16384 => ~11 GiB，会借走更多 cache slot。
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w805b_chunk_$STAMP.txt
SIZES=36000
REPS=${2:-2}
ORDER=${1:-AB}
WANT_ENV=13
cp "$CFG" /tmp/w805b_prod.json
restore_cfg() {
  cp /tmp/w805b_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W805b chunk size A=auto(8192) B=auto:16384  $STAMP size=$SIZES reps=$REPS order=$ORDER" > "$OUT"

setarm() {   # $1 = A|B
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
e = dict(d.get("env") or {})
e["STRATA_PREFILL_TIMING"] = "1"
d["env"] = e
a = list(d.get("args") or [])
while "--prefill" in a:
    i = a.index("--prefill")
    del a[i:i + 2]
a += ["--prefill", "auto" if arm == "A" else "auto:16384"]
d["args"] = a
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
PY
}

run() {
  local arm=$1
  setarm "$arm"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  local got pf
  got=$(docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null)
  pf=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -m1 "prompt chunk auto")
  echo "  ENVCHECK want=$WANT_ENV got=${got:-?} :: ${pf:-no chunk line}" >> "$OUT"
  if [ "${got:-0}" != "$WANT_ENV" ]; then echo "!! ABORT env_n $got" >> "$OUT"; exit 1; fi
  python3 mt_read.py 8090 "$arm" "$DATA/w805b_$arm.json" "$SIZES" "$REPS" kl_pool2.json >> "$OUT" 2>&1
  [ -f "$DATA/w805b_$arm.json" ] || { echo "!! ABORT no JSON" >> "$OUT"; exit 1; }
  slice "$OUT" "prompt [0-9]+ tokens = [0-9]+ reused"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "borrows [0-9]+ cache slots|VRAM free" | sed 's/^/  MEM /' >> "$OUT"
}

for k in $(seq 0 $((${#ORDER} - 1))); do run "${ORDER:$k:1}"; done
echo "== DONE $OUT"
