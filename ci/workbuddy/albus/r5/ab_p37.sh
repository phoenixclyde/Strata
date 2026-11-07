#!/bin/bash
# W809: 草稿策略扫描（--spec / --spec-min-p）
#   背景：生产 --spec 4 --spec-min-p 0.70，但 W808 的 DT 行显示 avg T 只有 2.30、1.89 token/window
#         => 上限（spec 4，suffix draft 会把它抬到 6）远没用满，真正起截断作用的是 min_p 0.70。
#   判据（按 W808 的教训，不看端到端 tok/s）：DT 行的 ms/window ÷ tokens/window = ms/token，外加 drafts 接受率。
#   注意 --spec 是 CLI 参数（generate.cpp:2591），不走 env。
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w809_spec_$STAMP.txt
ARMS=${*:-"A B C D E A2"}

cp "$CFG" /tmp/w809_prod.json
restore_cfg() {
  cp /tmp/w809_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W809 spec/min-p sweep  $STAMP arms='$ARMS'" > "$OUT"
echo "#   A=(4,0.70)生产 B=(4,0.50) C=(4,0.85) D=(4,0.95) E=(6,0.50) F=(6,0.70) A2=A重复" >> "$OUT"

setarm() {   # $1=spec $2=min_p
  python3 - "$CFG" "$1" "$2" >> "$OUT" <<'PYX'
import json, sys
cfg, spec, mp = sys.argv[1], sys.argv[2], sys.argv[3]
base = json.load(open("/tmp/w809_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_DECODE_TIMING"] = "1"          # 只加仪器，不改行为
a = list(base.get("args") or [])
for k in ("--spec", "--spec-min-p"):
    while k in a:
        i = a.index(k); del a[i:i + 2]
a += ["--spec", spec, "--spec-min-p", mp]
d = dict(base)
d["env"] = e
d["args"] = a
assert set(d.keys()) == set(base.keys())          # CFGCHECK：顶层键不能丢（W806 的坑）
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d spec=%s min_p=%s args_n=%d" % (len(d), len(e), spec, mp, len(a)))
PYX
}

run() {   # $1=arm $2=spec $3=min_p
  local arm=$1 spec=$2 mp=$3
  setarm "$spec" "$mp"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm spec=$spec min_p=$mp ready=${ok}s" >> "$OUT"
  # 自证：引擎自己的启动命令行（逐字含 --spec N --spec-min-p P）——日志里没有单独的 "verify window up to" banner
  grep -a "engine started:" "$LOG" | tail -1 | grep -oE "\-\-spec [0-9.]+|--spec-min-p [0-9.]+" | tr '\n' ' ' | sed 's/^/  VW /' >> "$OUT"
  echo >> "$OUT"
  python3 mt_gen.py 8090 "$arm" "$DATA/w809_gen_$arm.json" dec_corpus.json 200 3 >> "$OUT" 2>&1
  # 每次请求各一条 DT 行 => 全抓（不能 tail -1，否则只拿到第 3 条 prompt）
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "strata decode timing" | sed 's/^/  DT /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "drafts accepted" | tail -3 | cut -c1-170 | sed 's/^/  DA /' >> "$OUT"
  python3 -c "import json;d=json.load(open('$DATA/w809_gen_$arm.json'));print('  OKN %d/%d' % (len([r for r in d['results'] if r.get('ok')]), len(d['results'])))" >> "$OUT"
  # 更深的窗口会不会挤压专家槽（spec 6 => 有效 8 = kVerifyMaxT 上限）
  curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('  POOL slots=%d vram=%d' % (e['expert_slots'], e['vram_free_mib']))" >> "$OUT" 2>&1
}

for a in $ARMS; do
  case "$a" in
    A)  run A  4 0.70 ;;
    B)  run B  4 0.50 ;;
    C)  run C  4 0.85 ;;
    D)  run D  4 0.95 ;;
    E)  run E  6 0.50 ;;
    F)  run F  6 0.70 ;;
    A2) run A2 4 0.70 ;;
    *)  echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w809_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
