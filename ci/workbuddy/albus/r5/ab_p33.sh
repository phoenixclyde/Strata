#!/bin/bash
# W807b: RT_SKIP 的任务级门（36 题，判答对/答错）
#   目的：W807 的贪心发散只能说明「答案会变」，判不了「变好还是变坏」。这层补上准确率。
#   臂：A=RT_SKIP 7（生产值）  A2=A 重复（分数本身的稳定性）  B=RT_SKIP 0
#   全部 share=0（隔离解码侧），max_tokens 64，temperature 0，reasoning_effort none（与 W804 同口径）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w807b_task_$STAMP.txt
MAXT=64
ARMS=${*:-"A A2 B"}
N_TASK=$(python3 -c "import json;print(len(json.load(open('task_corpus.json'))['tasks']))")

cp "$CFG" /tmp/w807b_prod.json
restore_cfg() {
  cp /tmp/w807b_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W807b RT_SKIP task gate $STAMP max_tokens=$MAXT tasks=$N_TASK arms='$ARMS'" > "$OUT"
python3 -c "import json,hashlib;b=open('task_corpus.json','rb').read();print('  corpus sha16=%s bytes=%d'%(hashlib.sha256(b).hexdigest()[:16],len(b)))" >> "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d keys=%d'%(len(d['env']),len(d)))" >> "$OUT"

setarm() {   # $1=arm $2=rtskip
  python3 - "$CFG" "$2" >> "$OUT" <<'PY'
import json, sys
cfg, rt = sys.argv[1], sys.argv[2]
base = json.load(open("/tmp/w807b_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_PREFILL_CPU_SHARE"] = "0"
e["STRATA_ROUTE_TAIL_SKIP"] = rt
d = dict(base)
d["env"] = e
d["args"] = list(base.get("args") or [])
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d rtskip=%s" % (len(d), len(e), e.get("STRATA_ROUTE_TAIL_SKIP")))
PY
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

run() {   # $1=arm $2=rtskip
  local arm=$1 rt=$2
  setarm "$arm" "$rt"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm rtskip=$rt ready=${ok}s" >> "$OUT"
  check_env
  python3 mt_task.py 8090 "$arm" "$DATA/w807b_task_$arm.json" task_corpus.json "$MAXT" >> "$OUT" 2>&1
  if [ ! -f "$DATA/w807b_task_$arm.json" ]; then echo "!! ABORT no json" >> "$OUT"; exit 1; fi
  echo "  SCORE $arm = $(python3 -c "import json;d=json.load(open('$DATA/w807b_task_$arm.json'));print('%d/%d'%(d['score'],d['n']))")" >> "$OUT"
  echo "  tail_skip_line=$(grep -a 'route tail skip' "$OUT" | tail -1 | cut -c1-70)" >> "$OUT"
}

for a in $ARMS; do
  case "$a" in
    A)  run A  7 ;;
    A2) run A2 7 ;;
    B)  run B  0 ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w807b_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
