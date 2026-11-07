#!/bin/bash
# W813：`--ple-io ram` 的第二面 —— 解码侧与专家槽位
#
# W812 的 RD 臂（先 drop_caches 再启 ram）证明表**能**留住：PLEMAP rss 25.0-25.6 GB，
#   2560 token 的 read **4334 ms（591 tok/s）**，同尺寸 direct 基线 4997 ms（A/A2 在 2498 token 上）=> **-13~14%**。
#   但 W810 的 C 臂（表被换出）解码中位 42.44，而 A/A2 是 47.28/51.52 => 表不在时解码掉 10-14%。
# 本车要回答的唯一问题：**表留住之后，解码是否也回来了**（以及 `--expert-cache auto` 会不会因为多占 26.8 GB 而少给槽位）。
#   臂：P=生产 RR=ram P2=生产（交错，规则：A/B 交错 + 自有库）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w813_ramdec_$STAMP.txt
ARMS=${*:-"P RR P2"}

cp "$CFG" /tmp/w813_prod.json
DONE=0
restore_cfg() {
  [ "$DONE" = "1" ] && return 0          # 正常收尾已经恢复过，trap 不再重复重启（省 2 分钟）
  DONE=1
  cp /tmp/w813_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W813 ram decode check $STAMP arms='$ARMS'" > "$OUT"
docker cp /home/albus/strata166/tmp/plemap.sh strata166-407:/tmp/plemap.sh >/dev/null 2>&1
pm() { docker exec strata166-407 bash /tmp/plemap.sh 2>/dev/null | sed 's/^/    /' >> "$OUT"; }
slots() {
  curl -s --max-time 8 http://127.0.0.1:8090/metrics 2>/dev/null \
    | python3 -c "import sys,json
try:
    e=json.load(sys.stdin)['engine']; print('  POOL slots=%s vram=%s' % (e.get('expert_slots'), e.get('vram_free_mib')))
except Exception as ex: print('  POOL ?', ex)" >> "$OUT"
}

setarm() {   # $1=arm
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
io_mode = "ram" if arm == "RR" else None
base = json.load(open("/tmp/w813_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_PREFILL_TIMING"] = "1" if arm == "RR" else e.get("STRATA_PREFILL_TIMING", "0")
if arm != "RR":
    e.pop("STRATA_PREFILL_TIMING", None)
a = list(base.get("args") or [])
if "--ple-io" in a:
    del a[a.index("--ple-io"):a.index("--ple-io") + 2]
if io_mode:
    a += ["--ple-io", io_mode]
d = dict(base)
d["env"] = e
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d args_n=%d ple_io=%s" % (len(d), len(e), len(a), io_mode or "direct(缺省)"))
PY
}

run() {   # $1=arm
  local arm=$1 ok=0
  setarm "$arm" >> "$OUT"
  mark "$OUT"
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  echo "=== ARM $arm ready=${ok}s" >> "$OUT"
  [ "$ok" = "0" ] && { echo "!! ABORT never ready" >> "$OUT"; echo ABORT; exit 1; }
  pm; slots
  if [ "$arm" = "RR" ]; then
    python3 mt_read.py 8090 "$arm" "$DATA/w813_read_$arm.json" 2600 2 kl_pool.json >> "$OUT" 2>&1
    tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prompt [0-9]+ tokens = [0-9]+ reused" | cut -c1-130 | sed 's/^/  PL /' >> "$OUT"
    tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
    tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: host: chunk setup" | sed 's/^/  PHH /' >> "$OUT"
    pm
  fi
  python3 mt_gen.py 8090 "$arm" "$DATA/w813_gen_$arm.json" dec_corpus.json 128 3 >> "$OUT" 2>&1
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "strata decode timing" | sed 's/^/  DT /' >> "$OUT"
  pm; slots
  echo >> "$OUT"
}

for a in $ARMS; do run "$a"; done

DONE=1
cp /tmp/w813_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d args_n=%d ple_io=%s'%(len(d['env']),len(d['args']),'--ple-io' in d['args']))" >> "$OUT"
echo "== DONE $OUT"
