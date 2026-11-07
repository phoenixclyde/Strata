#!/bin/bash
# W806: 给「确定性开关」定 KL 绝对标尺 —— 用**已采纳**的 4 个开关在 W803 语料上量
#   背景：W805 发现规则 X（变更 <= 同配置两遍）对确定性开关天然失效（底噪恰好 0），P131 无法结案。
#   做法：全部臂把 share 钉 0（=> prefill 确定性），只逐个摘掉一个已采纳的开关，量它自己的 KL。
#   目的：得到「一个我们认可的开关在这个统计量上是多大」，再拿 P131 的 0.060 去比。
#   臂：A=生产(share0)  B=-HIP_PROMPT_F16  C=-ATTN_QUERY_SWIZZLE  D=-GDN_HEAD/PP  E=-ROUTE_TAIL_SKIP  F=A 重复
#   用法：ab_p29.sh [A|B|C|D|E|F ...]
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w806_ruler_$STAMP.txt
SHORT_READ=300
ARMS=${*:-"A B C D E F"}

cp "$CFG" /tmp/w806_prod.json
restore_cfg() {
  cp /tmp/w806_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W806 determinism ruler $STAMP short_read=$SHORT_READ arms='$ARMS'" > "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d args_n=%d prefill=%s'%(len(d['env']),len(d['args']),d['args'][d['args'].index('--prefill')+1]))" >> "$OUT"

setarm() {   # $1=arm $2=逗号分隔的「要摘掉的 key」
  python3 - "$CFG" "$1" "$2" "$SHORT_READ" <<'PY'
import json, sys
cfg, tag, drop, sr = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
base = json.load(open("/tmp/w806_prod.json"))          # 始终从生产副本出发，避免累积
e = dict(base.get("env") or {})
for k in [x for x in drop.split(",") if x]:
    e.pop(k, None)
e["STRATA_PREFILL_CPU_SHARE"] = "0"                     # 全程钉 0 => 确定性 prefill
e["STRATA_LOGPOS"] = "/data/w806_logpos_%s.tsv" % tag
e["STRATA_LOGPOS_TOPK"] = "64"
d = dict(base)                     # 保留 model/tokenizer/port/... 全部键；只换 env 与 args
d["env"] = e
a = list(base.get("args") or [])
while "--short-read" in a:
    i = a.index("--short-read"); del a[i:i + 2]
a += ["--short-read", sr]
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d" % (len(d), len(e)))
PY
}

check_env() {  # 断言引擎进程的 STRATA_* 集合 == 配置里的集合（规则 U：取证等级最高的一档）
  local arm=$1
  docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep "^STRATA_" | sort' 2>/dev/null > /tmp/.env_proc
  python3 - "$CFG" /tmp/.env_proc >> "$OUT" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
# 子集语义：配置里的每个 STRATA_* 必须出现在引擎进程里且值相同；
# 进程里多出来的只允许是**镜像级 ENV**（STRATA_SRC=/src 由 Dockerfile 的 ENV 带入，不在 config 里）
ALLOW = {"STRATA_SRC"}
want = sorted("%s=%s" % (k, v) for k, v in (cfg.get("env") or {}).items() if k.startswith("STRATA_"))
got = [l.strip() for l in open(sys.argv[2], encoding="utf-8", errors="replace") if l.strip()]
missing = sorted(set(want) - set(got))
extra = sorted(x for x in (set(got) - set(want)) if x.split("=", 1)[0] not in ALLOW)
ok = not missing and not extra
print("  ENVCHECK want=%d got=%d img_extra=%d %s"
      % (len(want), len(got), len(set(got) - set(want)) - len(extra), "OK" if ok else "MISMATCH"))
for x in missing: print("    missing-in-proc: " + x)
for x in extra:   print("    unexpected: " + x)
PY
  grep -q "ENVCHECK.*MISMATCH" "$OUT" && { echo "!! ABORT env mismatch" >> "$OUT"; exit 1; }
}

run() {   # $1=arm $2=drop
  local arm=$1 drop=$2
  rm -f "$DATA/w806_logpos_$arm.tsv"
  setarm "$arm" "$drop" >> "$OUT"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm drop='${drop:-none}' ready=${ok}s" >> "$OUT"
  check_env "$arm"
  python3 mt_kl.py kl_corpus.json 8090 "$arm" "$DATA/w806_kl_$arm.json" >> "$OUT" 2>&1
  if [ -f "$DATA/w806_logpos_$arm.tsv" ]; then
    echo "  LOGPOS rows=$(wc -l < "$DATA/w806_logpos_$arm.tsv") bytes=$(stat -c%s "$DATA/w806_logpos_$arm.tsv") md5=$(md5sum < "$DATA/w806_logpos_$arm.tsv" | cut -c1-12)" >> "$OUT"
  else
    echo "  LOGPOS MISSING" >> "$OUT"; echo "!! ABORT no logpos" >> "$OUT"; exit 1
  fi
}

for a in $ARMS; do
  case "$a" in
    A) run A "" ;;
    B) run B "STRATA_HIP_PROMPT_F16" ;;
    C) run C "STRATA_GFX906_ATTN_QUERY_SWIZZLE" ;;
    D) run D "STRATA_GDN_HEAD,STRATA_GDN_PP" ;;
    E) run E "STRATA_ROUTE_TAIL_SKIP" ;;
    F) run F "" ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w806_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d share=%s'%(len(d['env']),d['env'].get('STRATA_PREFILL_CPU_SHARE')))" >> "$OUT"
echo "== DONE $OUT"
