#!/bin/bash
# W807 解码侧质量门：长生成贪心发散（同配置两遍 = 底噪）
#   为什么不用 LOGPOS：它只在 prompt 的 read_windows 落行（generate.cpp:13084 唯一调用点），
#   而 tail skip 要求「窗口内每个 token 都把该缺失专家路由到 rank>=7」（expert_source.cpp:4857-4879），
#   60-190 长的窗口上这几乎不成立 => 解码侧必须另有仪器。
#   臂（全部 share=0 + --short-read 0，=> prefill 确定、prompt 走 batched）：
#     A = RT_SKIP 7（生产值）   A2 = A 重复（底噪）   B = RT_SKIP 0
#     C = 摘 GDN_HEAD+GDN_PP    D = 摘 GFX906_ATTN_QUERY_SWIZZLE
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w807_dec_$STAMP.txt
ARMS=${*:-"A A2 B C D"}
MAXT=600

cp "$CFG" /tmp/w807_prod.json
restore_cfg() {
  cp /tmp/w807_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W807 decode-side gate (greedy long generation) $STAMP arms='$ARMS' maxt=$MAXT" > "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d keys=%d'%(len(d['env']),len(d)))" >> "$OUT"

setarm() {   # $1=arm $2=drop(逗号分隔) $3=rtskip 值
  python3 - "$CFG" "$1" "$2" "$3" >> "$OUT" <<'PY'
import json, sys
cfg, tag, drop, rt = sys.argv[1:5]
base = json.load(open("/tmp/w807_prod.json"))
e = dict(base.get("env") or {})
for k in [x for x in drop.split(",") if x]:
    e.pop(k, None)
e["STRATA_PREFILL_CPU_SHARE"] = "0"                  # 确定性 prefill
e["STRATA_ROUTE_TAIL_SKIP"] = rt
d = dict(base)
d["env"] = e
a = list(base.get("args") or [])
while "--short-read" in a:
    i = a.index("--short-read"); del a[i:i + 2]
a += ["--short-read", "0"]                           # prompt 一律走 batched（不经窗口）
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d rtskip=%s drop='%s'" % (len(d), len(e), e.get("STRATA_ROUTE_TAIL_SKIP"), drop))
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

run() {   # $1=arm $2=drop $3=rtskip
  local arm=$1 drop=${2:-} rt=${3:-7}
  setarm "$arm" "$drop" "$rt"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm rtskip=$rt drop='${drop:-none}' ready=${ok}s" >> "$OUT"
  check_env
  # 预热一次（丢掉冷启动），再正式跑
  python3 mt_decq.py 8090 "${arm}_warm" "$DATA/w807_decq_${arm}_warm.json" dec_corpus.json 8 >> "$OUT" 2>&1
  python3 mt_decq.py 8090 "$arm" "$DATA/w807_decq_$arm.json" dec_corpus.json "$MAXT" >> "$OUT" 2>&1
  if [ ! -f "$DATA/w807_decq_$arm.json" ]; then echo "!! ABORT no json" >> "$OUT"; exit 1; fi
  echo "  tail_skip_line=$(tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" 2>/dev/null | grep -a 'route tail skip' | tail -1 | cut -c1-90)" >> "$OUT"
}

for a in $ARMS; do
  case "$a" in
    A)  run A  "" 7 ;;
    A2) run A2 "" 7 ;;
    B)  run B  "" 0 ;;
    C)  run C  "STRATA_GDN_HEAD,STRATA_GDN_PP" 7 ;;
    D)  run D  "STRATA_GFX906_ATTN_QUERY_SWIZZLE" 7 ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w807_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
