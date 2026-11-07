#!/bin/bash
# W807c: ATTN_QUERY_SWIZZLE 的任务级门（36 题，判答对/答错）
#   动机：W807a 的贪心发散里 swizzle 也会让文本分叉（4/6 条），但它只换 1.6% 的 decode
#   => 需要准确率这一层，才能判断"改答案"有没有代价。
#   臂：A=swizzle 开（生产值）  A2=A 重复  B=swizzle 关
#   全部 share=0（隔离解码侧），max_tokens 64，temperature 0，reasoning_effort none（与 W804/W807b 同口径）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w807c_task_$STAMP.txt
MAXT=64
ARMS=${*:-"A A2 B"}
N_TASK=$(python3 -c "import json;print(len(json.load(open('task_corpus.json'))['tasks']))")

cp "$CFG" /tmp/w807c_prod.json
restore_cfg() {
  cp /tmp/w807c_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W807c swizzle task gate $STAMP max_tokens=$MAXT tasks=$N_TASK arms='$ARMS'" > "$OUT"
python3 -c "import json,hashlib;b=open('task_corpus.json','rb').read();print('  corpus sha16=%s bytes=%d'%(hashlib.sha256(b).hexdigest()[:16],len(b)))" >> "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d keys=%d'%(len(d['env']),len(d)))" >> "$OUT"

setarm() {   # $1=drop(逗号分隔)
  python3 - "$CFG" "$1" >> "$OUT" <<'PYX'
import json, sys
cfg, drop = sys.argv[1], sys.argv[2]
base = json.load(open("/tmp/w807c_prod.json"))
e = dict(base.get("env") or {})
for k in [x for x in drop.split(",") if x]:
    e.pop(k, None)
e["STRATA_PREFILL_CPU_SHARE"] = "0"
d = dict(base)
d["env"] = e
d["args"] = list(base.get("args") or [])
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d drop='%s'" % (len(d), len(e), drop))
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

run() {   # $1=arm $2=drop
  local arm=$1 drop=${2:-}
  setarm "$drop"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm drop='${drop:-none}' ready=${ok}s" >> "$OUT"
  check_env
  python3 mt_task.py 8090 "$arm" "$DATA/w807c_task_$arm.json" task_corpus.json "$MAXT" >> "$OUT" 2>&1
  if [ ! -f "$DATA/w807c_task_$arm.json" ]; then echo "!! ABORT no json" >> "$OUT"; exit 1; fi
  echo "  SCORE $arm = $(python3 -c "import json;d=json.load(open('$DATA/w807c_task_$arm.json'));print('%d/%d'%(d['score'],d['n']))")" >> "$OUT"
}

for a in $ARMS; do
  case "$a" in
    A)  run A  "" ;;
    A2) run A2 "" ;;
    B)  run B  "STRATA_GFX906_ATTN_QUERY_SWIZZLE" ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w807c_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
