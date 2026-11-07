#!/bin/bash
# W809b: 第二轮
#   背景（全部源码可核）：
#     1) `src/core/nv_defaults.cpp:22-46` 的「NVIDIA 精确加速开关」只给 sm_86 与 sm_60 填表
#        （sm_86 整套 +9.6%/+14.6%，8/8 对）；`arch_defaults.cpp` 只给 gfx12/gfx1151
#        => **gfx906 两套默认表都是空的，这些融合一个都没开**。W808 的扫描器只找 `#if` 形式，抓不到这类运行时 setenv 表。
#     2) `iq_kernels.cu:4106` 逐字：STRATA_GU_SWIGLU「bitwise the same hq」，非 12.0 卡可用 =1 强制开。
#     3) `native_mmvq.cu:3262` `#else // HIP: no interleaved path` 且外层是 `#if !defined(__HIPCC__)`
#        => MMVQ-IL（2..4 列）在 HIP 构建里被编译掉，STRATA_MMVQ_IL_ROWS 是死旋钮（不再花 GPU 时间）。
#   臂：P=生产  S=融合整套  Q=min_p 0.50  S2=S重复  P2=P重复
#   判据：DT 行的 ms/window ÷ tokens/window（引擎内部，不含客户端）；每条臂 6 个 prompt，分析时丢前 2 个（冷启）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w809b_fuse_$STAMP.txt
ARMS=${*:-"P S Q S2 P2"}

# 融合整套：名字全部来自 nv_defaults.cpp 的 sm_86 表（去掉只对 sm_86/sm_60 有意义的 ADAPT_LAG 之外的都在）
STACK="STRATA_SIDE_MIXER=2 STRATA_ATTN_DAILY=1 STRATA_GR_UP75=1 STRATA_GU_SWIGLU=1 STRATA_QSA_ROWS=1 STRATA_B6_MMVQ_ROWS=1 STRATA_ADAPT_NOWAIT=1 STRATA_ADAPT_LAG=2 STRATA_CPU_IQ_ALL_EXACT1=1"

cp "$CFG" /tmp/w809b_prod.json
restore_cfg() {
  cp /tmp/w809b_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W809b fusion stack  $STAMP arms='$ARMS'" > "$OUT"
echo "#   stack = $STACK" >> "$OUT"

setarm() {   # $1=spec $2=min_p $3=extra env("K=V K=V")
  python3 - "$CFG" "$1" "$2" "$3" >> "$OUT" <<'PYX'
import json, sys
cfg, spec, mp, extra = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
base = json.load(open("/tmp/w809b_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_DECODE_TIMING"] = "1"
for kv in extra.split():
    k, v = kv.split("=", 1)
    e[k] = v
a = list(base.get("args") or [])
for k in ("--spec", "--spec-min-p"):
    while k in a:
        i = a.index(k); del a[i:i + 2]
a += ["--spec", spec, "--spec-min-p", mp]
d = dict(base)
d["env"] = e
d["args"] = a
assert set(d.keys()) == set(base.keys())
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d spec=%s min_p=%s extra=%d" % (len(d), len(e), spec, mp, len(extra.split())))
PYX
}

run() {   # $1=arm $2=spec $3=min_p $4=extra
  local arm=$1 spec=$2 mp=$3 extra=${4:-}
  setarm "$spec" "$mp" "$extra"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM $arm spec=$spec min_p=$mp nenv=$(( $(echo "$extra" | wc -w) )) ready=${ok}s" >> "$OUT"
  # 自证 1：引擎命令行里的 spec
  grep -a "engine started:" "$LOG" | tail -1 | grep -oE "\-\-spec [0-9.]+|--spec-min-p [0-9.]+" | tr '\n' ' ' | sed 's/^/  VW /' >> "$OUT"
  echo >> "$OUT"
  # 自证 2：融合开关是否真的进了引擎进程
  docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); tr "\0" "\n" < /proc/$p/environ' 2>/dev/null \
    | grep -cE "^(STRATA_SIDE_MIXER|STRATA_ATTN_DAILY|STRATA_GR_UP75|STRATA_GU_SWIGLU|STRATA_QSA_ROWS|STRATA_B6_MMVQ_ROWS|STRATA_ADAPT_NOWAIT|STRATA_ADAPT_LAG|STRATA_CPU_IQ_ALL_EXACT1)=" \
    | sed 's/^/  FUSECHECK engine_env_hits=/' >> "$OUT"
  python3 mt_gen.py 8090 "$arm" "$DATA/w809b_gen_$arm.json" dec_corpus.json 200 6 >> "$OUT" 2>&1
  if [ ! -f "$DATA/w809b_gen_$arm.json" ]; then
    echo "!! ABORT: client produced no JSON for arm $arm (engine down?)" >> "$OUT"; echo "ABORT"; exit 1
  fi
  python3 -c "import json;d=json.load(open('$DATA/w809b_gen_$arm.json'));print('  OKN %d/%d' % (len([r for r in d['results'] if r.get('ok')]), len(d['results'])))" >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "strata decode timing" | sed 's/^/  DT /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "drafts accepted" | tail -6 | cut -c1-170 | sed 's/^/  DA /' >> "$OUT"
  curl -s --max-time 8 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('  POOL slots=%d vram=%d' % (e['expert_slots'], e['vram_free_mib']))" >> "$OUT" 2>&1
}

for a in $ARMS; do
  case "$a" in
    P)  run P  4 0.70 "" ;;
    S)  run S  4 0.70 "$STACK" ;;
    Q)  run Q  4 0.50 "" ;;
    S2) run S2 4 0.70 "$STACK" ;;
    P2) run P2 4 0.70 "" ;;
    Q2) run Q2 4 0.50 "" ;;
    *)  echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w809b_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
