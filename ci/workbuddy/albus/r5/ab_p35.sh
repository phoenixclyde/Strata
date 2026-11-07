#!/bin/bash
# W808: 「CUDA 默认开 / HIP 默认关」那一类开关的解码侧 A/B
#   来源：albus/w808/scan_hip_defaults.py 扫出 8 个此类函数，取其中三个真正可能白丢收益的：
#     H = STRATA_HEAD_MIX_MULTI=1        head 的 HC 读按窗口一次发（源码注释逐字：bitwise the same sums）
#     F = STRATA_FUSE_HITS=1             moe_hit_add 折进 combine（gfx12 默认开；正是 VRAM hits 那一项）
#     O = STRATA_ONE_TOKEN_COMMIT=1      单 token 窗口自己推进状态，commit 不再发一张图（CUDA 默认开）
#   判据：decode tok/s（服务端 decode_ms，3 条不同 prompt × 200 token），臂间 >3% 才算；赢的再过质量门
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w808_hipdef_$STAMP.txt
MAXT=200
ARMS=${*:-"P H F O"}

cp "$CFG" /tmp/w808_prod.json
restore_cfg() {
  cp /tmp/w808_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W808 HIP-default A/B $STAMP maxt=$MAXT arms='$ARMS'" > "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d keys=%d'%(len(d['env']),len(d)))" >> "$OUT"

setarm() {   # $1=要加的 KEY=VALUE（可空）
  python3 - "$CFG" "$1" >> "$OUT" <<'PYX'
import json, sys
cfg, add = sys.argv[1], sys.argv[2]
base = json.load(open("/tmp/w808_prod.json"))
e = dict(base.get("env") or {})
if add:
    k, v = add.split("=", 1)
    e[k] = v
d = dict(base)
d["env"] = e
d["args"] = list(base.get("args") or [])
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d add='%s'" % (len(d), len(e), add or "none"))
PYX
}

check_env() {
  docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep "^STRATA_" | sort' 2>/dev/null > /tmp/.env_proc
  python3 - "$CFG" /tmp/.env_proc >> "$OUT" <<'PY'
import json, sys
ALLOW = {"STRATA_SRC"}
cfg = json.load(open(sys.argv[1]))
want = sorted("%s=%s" % (k, v) for k, v in (cfg.get("env") or {}).items() if k.startswith("STRATA_"))
got = [l.strip() for l in open(sys.argv[2], encoding="utf-8", errors="replace") if l.strip()]
missing = sorted(set(want) - set(got))
extra = sorted(x for x in (set(got) - set(want)) if x.split("=", 1)[0] not in ALLOW)
print("  ENVCHECK want=%d got=%d %s" % (len(want), len(got), "OK" if not missing and not extra else "MISMATCH"))
for x in missing: print("    missing-in-proc: " + x)
for x in extra:   print("    unexpected: " + x)
PY
  grep -q "ENVCHECK.*MISMATCH" "$OUT" && { echo "!! ABORT env mismatch" >> "$OUT"; exit 1; }
}

run() {   # $1=arm $2=add
  local arm=$1 add=${2:-}
  setarm "$add"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm add='${add:-none}' ready=${ok}s" >> "$OUT"
  check_env
  python3 mt_gen.py 8090 "$arm" "$DATA/w808_gen_$arm.json" dec_corpus.json "$MAXT" 3 >> "$OUT" 2>&1
  if [ ! -f "$DATA/w808_gen_$arm.json" ]; then echo "!! ABORT no json" >> "$OUT"; exit 1; fi
}

for a in $ARMS; do
  case "$a" in
    P) run P "" ;;
    H) run H "STRATA_HEAD_MIX_MULTI=1" ;;
    F) run F "STRATA_FUSE_HITS=1" ;;
    O) run O "STRATA_ONE_TOKEN_COMMIT=1" ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w808_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
