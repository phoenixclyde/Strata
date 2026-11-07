#!/bin/bash
# W806c: PR #4158（STRATA_PF_MMVQ）的质量门 —— 在 MMVQ 真正生效的尺寸上量 teacher-forced KL
#   语料 kl_corpus4：shape 轮 fresh 222-231 token（<= MAX_T 256 => MMVQ 生效，且 > short_read 80 => 走 prefill）
#                    probe 轮 fresh 58-64 token（<= short_read 80 => verify 窗口 => LOGPOS 落行）
#   臂（全部用 p6 二进制 + share=0 => 确定性基线）：
#     A = MMVQ 关           B = MMVQ=1(MAX_T 256)      C = B 重复（判 MMVQ 自身确定性）
#     D = MMVQ 关 + 摘掉 HIP_PROMPT_F16（已采纳开关的**同语料参考量程**）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAGE=/src/build-906/_staged
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w806c_klmmvq_$STAMP.txt
SHORT_READ=80
ARMS=${*:-"A B C D"}

cp "$CFG" /tmp/w806c_prod.json
restore_cfg() {
  cp /tmp/w806c_prod.json "$CFG" 2>/dev/null
  docker exec strata166-407 bash -lc "cp $STAGE/strata_p4 /src/build-906/strata.new && mv -f /src/build-906/strata.new /src/build-906/strata" 2>&1 | sed 's/^/    bin-swap: /' >> "$OUT"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W806c MMVQ KL gate $STAMP short_read=$SHORT_READ arms='$ARMS'" > "$OUT"
docker exec strata166-407 bash -lc "md5sum $STAGE/strata_p6" 2>/dev/null | sed 's/^/  bin /' >> "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d keys=%d'%(len(d['env']),len(d)))" >> "$OUT"

setarm() {   # $1=arm $2=mmvq(0|1) $3=maxt $4=要摘掉的 key
  python3 - "$CFG" "$2" "$3" "$4" "$SHORT_READ" "$1" >> "$OUT" <<'PY'
import json, sys
cfg, mmvq, maxt, drop, sr, tag = sys.argv[1:7]
base = json.load(open("/tmp/w806c_prod.json"))
e = dict(base.get("env") or {})
for k in [x for x in drop.split(",") if x]:
    e.pop(k, None)
e.pop("STRATA_PF_MMVQ", None); e.pop("STRATA_PF_MMVQ_MAX_T", None)
e["STRATA_PREFILL_CPU_SHARE"] = "0"          # 确定性基线
if mmvq == "1":
    e["STRATA_PF_MMVQ"] = "1"
    if maxt:
        e["STRATA_PF_MMVQ_MAX_T"] = maxt
e["STRATA_LOGPOS"] = "/data/w806_logpos_%s.tsv" % tag
e["STRATA_LOGPOS_TOPK"] = "64"
d = dict(base)
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

check_env() {
  docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep "^STRATA_" | sort' 2>/dev/null > /tmp/.env_proc
  python3 - "$CFG" /tmp/.env_proc >> "$OUT" <<'PY'
import json, sys
ALLOW = {"STRATA_SRC"}          # 镜像级 ENV，不在 config 里
cfg = json.load(open(sys.argv[1]))
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

run() {   # $1=arm $2=mmvq $3=maxt $4=drop
  local arm=$1 mmvq=$2 maxt=${3:-} drop=${4:-}
  rm -f "$DATA/w806_logpos_$arm.tsv"
  setarm "$arm" "$mmvq" "$maxt" "$drop"
  docker exec strata166-407 bash -lc "cp $STAGE/strata_p6 /src/build-906/strata.new && mv -f /src/build-906/strata.new /src/build-906/strata" 2>&1 | sed 's/^/    bin-swap: /' >> "$OUT"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm mmvq=$mmvq maxt=${maxt:-def} drop='${drop:-none}' ready=${ok}s" >> "$OUT"
  check_env
  python3 mt_kl.py kl_corpus4.json 8090 "$arm" "$DATA/w806c_kl_$arm.json" >> "$OUT" 2>&1
  if [ -f "$DATA/w806_logpos_$arm.tsv" ]; then
    echo "  LOGPOS rows=$(wc -l < "$DATA/w806_logpos_$arm.tsv") md5=$(md5sum < "$DATA/w806_logpos_$arm.tsv" | cut -c1-12)" >> "$OUT"
  else
    echo "  LOGPOS MISSING" >> "$OUT"; echo "!! ABORT no logpos" >> "$OUT"; exit 1
  fi
}

for a in $ARMS; do
  case "$a" in
    A) run A 0 "" "" ;;
    B) run B 1 "256" "" ;;
    C) run C 1 "256" "" ;;
    D) run D 0 "" "STRATA_HIP_PROMPT_F16" ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w806c_prod.json "$CFG"
docker exec strata166-407 bash -lc "cp $STAGE/strata_p4 /src/build-906/strata.new && mv -f /src/build-906/strata.new /src/build-906/strata" 2>&1 | sed 's/^/    bin-swap: /' >> "$OUT"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
