#!/bin/bash
# W814：`--ple-io ram` 的确认车 —— 交错 A/B/A + 逐字答案指纹
#   W812 的 RD 臂给出 -14%（单臂，一次），而 W813 显示解码在 A 臂之间能有 13% 的宿主漂移
#   => 提示侧也要交错确认（规则：A/B 交错；>=5% 才判）。
#   另外：换了 PLE 取数路径，必须按逐字口径证明答案没变（`mt_hash.py`：temperature 0、固定 max_tokens、
#   取 content 的 sha256），不能只用「上游有 parity 测试」当证据。
#   臂：PA(生产) RA(ram) PB(生产)
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w814_confirm_$STAMP.txt
ARMS=${*:-"PA RA PB"}

cp "$CFG" /tmp/w814_prod.json
DONE=0
restore_cfg() {
  [ "$DONE" = "1" ] && return 0
  DONE=1
  cp /tmp/w814_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W814 ram confirm A/B/A $STAMP arms='$ARMS'" > "$OUT"
docker cp /home/albus/strata166/tmp/plemap.sh strata166-407:/tmp/plemap.sh >/dev/null 2>&1
pm() { docker exec strata166-407 bash /tmp/plemap.sh 2>/dev/null | sed 's/^/    /' >> "$OUT"; }

setarm() {   # $1=arm
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
io_mode = "ram" if arm.startswith("R") else None
base = json.load(open("/tmp/w814_prod.json"))
a = list(base.get("args") or [])
if "--ple-io" in a:
    del a[a.index("--ple-io"):a.index("--ple-io") + 2]
if io_mode:
    a += ["--ple-io", io_mode]
d = dict(base)
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d args_n=%d ple_io=%s"
      % (len(d), len(d.get("env") or {}), len(a), io_mode or "direct(缺省)"))
PY
}

run() {   # $1=arm
  local arm=$1 ok=0 t0 t1
  setarm "$arm" >> "$OUT"
  t0=$(date +%s)
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  t1=$(date +%s)
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s start_wall=$((t1 - t0))s" >> "$OUT"
  [ "$ok" = "0" ] && { echo "!! ABORT never ready" >> "$OUT"; echo ABORT; exit 1; }
  pm
  python3 mt_read.py 8090 "$arm" "$DATA/w814_read_$arm.json" 2600 2 kl_pool.json 0 >> "$OUT" 2>&1
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prompt [0-9]+ tokens = [0-9]+ reused" | cut -c1-135 | sed 's/^/  PL /' >> "$OUT"
  python3 mt_hash.py 8090 "$arm" dec_corpus.json 200 >> "$OUT" 2>&1
  pm
  echo >> "$OUT"
}

for a in $ARMS; do run "$a"; done

DONE=1
cp /tmp/w814_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d args_n=%d ple_io=%s'%(len(d['env']),len(d['args']),'--ple-io' in d['args']))" >> "$OUT"
echo "== DONE $OUT"
