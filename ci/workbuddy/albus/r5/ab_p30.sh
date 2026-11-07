#!/bin/bash
# W806b: PR #4158（STRATA_PF_MMVQ）的 A/B —— 换的是**引擎二进制**（p4 vs p6），不是容器/镜像
#   p6 与 p4 的唯一差异就是 gemm.cu/gemm.hpp 的 MMVQ 分支 => 二进制替换是忠实的，且可逆
#   臂：A=p4 B=p6(MMVQ 关) C=p6(MMVQ=1, MAX_T 缺省 256) D=p6(MMVQ=1, MAX_T 512) E=p4 重复
#   每臂：mt_chat（真实多轮）+ mt_read（单发 fresh，150/220 在阈值内、300/600 在阈值外）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w806b_mmvq_$STAMP.txt
STAGE=/src/build-906/_staged
ARMS=${*:-"A B C D E"}

cp "$CFG" /tmp/w806b_prod.json
restore_cfg() {
  cp /tmp/w806b_prod.json "$CFG" 2>/dev/null
  docker exec strata166-407 bash -lc "cp $STAGE/strata_p4 /src/build-906/strata.new && mv -f /src/build-906/strata.new /src/build-906/strata" 2>&1 | sed 's/^/    bin-swap: /' >> "$OUT"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W806b MMVQ A/B $STAMP arms='$ARMS'" > "$OUT"
docker exec strata166-407 bash -lc "mkdir -p $STAGE" 2>/dev/null
docker cp /home/albus/strata166/binaries/strata_p4 strata166-407:$STAGE/strata_p4 2>/dev/null
docker cp /home/albus/strata166/binaries/strata_p6 strata166-407:$STAGE/strata_p6 2>/dev/null
docker exec strata166-407 bash -lc "md5sum $STAGE/strata_p4 $STAGE/strata_p6" 2>/dev/null | sed 's/^/  bin /' >> "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d args_n=%d'%(len(d['env']),len(d['args'])))" >> "$OUT"

setarm() {   # $1=arm $2=bin(p4|p6) $3=MMVQ(0|1) $4=MAX_T
  python3 - "$CFG" "$3" "$4" <<'PY'
import json, sys
cfg, mmvq, maxt = sys.argv[1], sys.argv[2], sys.argv[3]
base = json.load(open("/tmp/w806b_prod.json"))
e = dict(base.get("env") or {})
e.pop("STRATA_PF_MMVQ", None); e.pop("STRATA_PF_MMVQ_MAX_T", None)
if mmvq == "1":
    e["STRATA_PF_MMVQ"] = "1"
    if maxt:
        e["STRATA_PF_MMVQ_MAX_T"] = maxt
d = dict(base)                     # 保留 model/tokenizer/port/... 全部键
d["env"] = e
d["args"] = list(base.get("args") or [])
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d" % (len(d), len(e)))
PY
}

check() {   # 断言：二进制指纹 + 引擎 env 集合
  local arm=$1 wantbin=$2
  local got
  got=$(docker exec strata166-407 bash -lc "md5sum /src/build-906/strata | cut -c1-32" 2>/dev/null | tr -d ' \r')
  local want
  want=$(docker exec strata166-407 bash -lc "md5sum $STAGE/strata_$wantbin | cut -c1-32" 2>/dev/null | tr -d ' \r')
  echo "  BINCHECK arm=$arm want=$wantbin md5=${got:0:12} ${want:0:12} $([ "$got" = "$want" ] && echo OK || echo MISMATCH)" >> "$OUT"
  [ "$got" = "$want" ] || { echo "!! ABORT binary mismatch" >> "$OUT"; exit 1; }
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

run() {   # $1=arm $2=bin $3=mmvq $4=maxt
  local arm=$1 bin=$2 mmvq=$3 maxt=${4:-}
  setarm "$arm" "$bin" "$mmvq" "$maxt" >> "$OUT"
  # 目标二进制正在被执行 => 直接 cp 会被 ETXTBSY 拒绝（且 2>/dev/null 会把它吞掉）。
  # 改成 cp 到 .new 再 mv（rename 对忙文件是原子的，旧 inode 继续服务正在跑的进程）。
  docker exec strata166-407 bash -lc "cp $STAGE/strata_$bin /src/build-906/strata.new && mv -f /src/build-906/strata.new /src/build-906/strata" 2>&1 | sed 's/^/    bin-swap: /' >> "$OUT"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm bin=$bin mmvq=$mmvq maxt=${maxt:-default} ready=${ok}s" >> "$OUT"
  check "$arm" "$bin"
  python3 mt_chat.py 80,280,80,280 64 >> "$OUT" 2>&1
  python3 mt_chat.py 80,280,80,280 64 >> "$OUT" 2>&1
  python3 mt_read.py 8090 "$arm" "$DATA/w806b_read_$arm.json" 150,220,300,600 2 kl_pool.json >> "$OUT" 2>&1
  if [ ! -f "$DATA/w806b_read_$arm.json" ]; then echo "!! ABORT no read json" >> "$OUT"; exit 1; fi
  echo "  read_results=$(python3 -c "import json;print(len(json.load(open('$DATA/w806b_read_$arm.json'))['results']))")" >> "$OUT"
}

for a in $ARMS; do
  case "$a" in
    A) run A p4 0 "" ;;
    B) run B p6 0 "" ;;
    C) run C p6 1 "256" ;;
    D) run D p6 1 "512" ;;
    E) run E p4 0 "" ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w806b_prod.json "$CFG"
docker exec strata166-407 bash -lc "cp $STAGE/strata_p4 /src/build-906/strata.new && mv -f /src/build-906/strata.new /src/build-906/strata" 2>&1 | sed 's/^/    bin-swap: /' >> "$OUT"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
