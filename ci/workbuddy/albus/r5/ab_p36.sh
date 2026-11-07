#!/bin/bash
# W808b(v2): 现役配置下的解码相位构成 —— 用 STRATA_DECODE_TIMING=1（不是 STRATA_TRACE）
#   generate.cpp:14044 `static const bool dec_timing = std::getenv("STRATA_DECODE_TIMING") != nullptr;`
#   它给的分解比 GPU stages 更全：verify(GPU-reach wait + per-layer host[plan actq jobs CPU] + stage)
#                                  + commit/emit + draft；per layer-window: CPU experts / VRAM hits / PCIe
#   臂：P=生产；O=ONE_TOKEN_COMMIT=1（上一车 decode -6.3%，用 commit/emit 这一项找原因）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w808c_dectiming_$STAMP.txt
ARMS=${*:-"P O"}

cp "$CFG" /tmp/w808c_prod.json
restore_cfg() {
  cp /tmp/w808c_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W808c decode timing (production config + STRATA_DECODE_TIMING=1) $STAMP arms='$ARMS'" > "$OUT"

setarm() {   # $1=要加的 KEY=VALUE（可空）
  python3 - "$CFG" "$1" >> "$OUT" <<'PYX'
import json, sys
cfg, add = sys.argv[1], sys.argv[2]
base = json.load(open("/tmp/w808c_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_DECODE_TIMING"] = "1"
if add:
    k, v = add.split("=", 1)
    e[k] = v
d = dict(base)
d["env"] = e
d["args"] = list(base.get("args") or [])
assert set(d.keys()) == set(base.keys())
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d add='%s'" % (len(d), len(e), add or "none"))
PYX
}

run() {   # $1=arm $2=add
  local arm=$1 add=${2:-}
  setarm "$add"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm add='${add:-none}' ready=${ok}s" >> "$OUT"
  python3 mt_gen.py 8090 "$arm" "$DATA/w808c_gen_$arm.json" dec_corpus.json 200 1 >> "$OUT" 2>&1
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "decode timing" | tail -1 | sed 's/^/  DT /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "decode GPU stages" | tail -1 | cut -c1-400 | sed 's/^/  PH /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "generated in" | tail -1 | cut -c1-190 | sed 's/^/  SV /' >> "$OUT"
}

for a in $ARMS; do
  case "$a" in
    P) run P "" ;;
    O) run O "STRATA_ONE_TOKEN_COMMIT=1" ;;
    F) run F "STRATA_FUSE_HITS=1" ;;
    H) run H "STRATA_HEAD_MIX_MULTI=1" ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w808c_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
