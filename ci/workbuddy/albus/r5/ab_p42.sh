#!/bin/bash
# W812：P138 的第二车 —— 两条独立的假设，各自可独立成立
#
# H-A（chunk 重叠）：A/B/C 三臂的 ple 都稳定在 12.9-16.7%（无差别）。源码给出的解释是
#   `ple_reader.hpp:5-14` 逐字 "kept at most max_inflight deep, so a chunk's reads can run while the
#   previous chunk computes" => **第二个 chunk 起 PLE 可以藏在前一个 chunk 的计算里**；
#   而 `--prefill auto`=8192 对 1.5-6K 的提示**只有一个 chunk**，PLE 全部暴露。
#   => 把 chunk 调小，只有第一个 chunk 付钱。
#
# H-B（ram 为什么只有第一个请求快）：W810 的 C 臂（--ple-io ram）第 1 个请求主机侧 PLE 只有 **23 ms**
#   （direct 是 294 ms），第 2 个起回到 647/1168 ms；跑完后 RssFile 只剩 **986 MB**（表 26.8 GiB 被换出）。
#   => 表被 touch 进来之后又被**页缓存回收**（引擎自己要 59.7 GB anon，机器 128 GB，
#      还有 ~40 GB 陈旧页缓存与新 touch 的页竞争）。若先清掉陈旧页缓存再启动，表可能留得住。
#   本车先用 `drop_caches` 复测；再叠 `--no-ple-prefetch`（#2918 逐字：POSIX 上它只关 gather_batch 里
#   每行一次的 MADV_WILLNEED）分辨「缺页」与「hint 本身的开销」。
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w812_ple2_$STAMP.txt
ARMS=${*:-"K4 K2 RD RDN"}
SIZES=1500,3000,6000

cp "$CFG" /tmp/w812_prod.json
restore_cfg() {
  cp /tmp/w812_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W812 P138 second car $STAMP arms='$ARMS'" > "$OUT"
docker cp /home/albus/strata166/tmp/plemap.sh strata166-407:/tmp/plemap.sh >/dev/null 2>&1
pm() { docker exec strata166-407 bash /tmp/plemap.sh 2>/dev/null | sed 's/^/    /' >> "$OUT"; }

setarm() {   # $1=arm
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
# (prefill, ple_io, extra args)
SPEC = {"K4": ("4096", None, []), "K2": ("2048", None, []),
        "RD": ("auto", "ram", []), "RDN": ("auto", "ram", ["--no-ple-prefetch"])}
pf, io_mode, extra = SPEC[arm]
base = json.load(open("/tmp/w812_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_PREFILL_TIMING"] = "1"
e["STRATA_DECODE_TIMING"] = "1"
a = list(base.get("args") or [])
for k in ("--ple-io", "--no-ple-prefetch"):
    while k in a:
        del a[a.index(k):a.index(k) + (2 if k == "--ple-io" else 1)]
a[a.index("--prefill") + 1] = pf
if io_mode:
    a += ["--ple-io", io_mode]
a += extra
d = dict(base)
d["env"] = e
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d prefill=%s ple_io=%s extra=%s"
      % (len(d), len(e), pf, io_mode or "direct(缺省)", " ".join(extra) or "-"))
PY
}

boot() {   # $1=arm  $2=drop(1|0)
  local arm=$1 drop=${2:-0} ok=0 t0 t1
  t0=$(date +%s)
  if [ "$drop" = "1" ]; then
    sudo -n sh -c "sync; echo 1 > /proc/sys/vm/drop_caches" 2>/dev/null
    echo "  DROPCACHES done" >> "$OUT"; pm
  fi
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  t1=$(date +%s)
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s start_wall=$((t1 - t0))s drop=$drop" >> "$OUT"
  [ "$ok" = "0" ] && { echo "!! ABORT never ready" >> "$OUT"; echo ABORT; exit 1; }
  grep -a -E "PLE table .* in [0-9.]+ s|mlock failed|PLE direct read probe" "$LOG" | tail -2 | cut -c1-160 | sed 's/^/  MODE /' >> "$OUT"
  pm
}

req() {   # $1=arm $2=n-th  （单发 3000 token，fresh 文本：换语料起点，避免前缀命中会话缓存）
  local arm=$1 n=$2
  local start=$(( (n - 1) * 400 ))
  python3 mt_read.py 8090 "$arm$n" "$DATA/w812_r_${arm}_$n.json" 3000 1 kl_pool.json "$start" >> "$OUT" 2>&1 || true
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prompt [0-9]+ tokens = " | tail -1 | cut -c1-130 | sed "s/^/  PL$n /" >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | tail -1 | sed "s/^/  PH$n /" >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: host: chunk setup" | tail -1 | sed "s/^/  PHH$n /" >> "$OUT"
  echo "  -- after req$n" >> "$OUT"; pm
  mark "$OUT"
}

run_sweep() {   # $1=arm  $2=drop
  local arm=$1
  setarm "$arm" >> "$OUT"
  boot "$arm" "${2:-0}"
  python3 mt_read.py 8090 "$arm" "$DATA/w812_read_$arm.json" "$SIZES" 2 kl_pool.json >> "$OUT" 2>&1
  if [ ! -f "$DATA/w812_read_$arm.json" ]; then echo "!! ABORT no json $arm" >> "$OUT"; echo ABORT; exit 1; fi
  python3 -c "import json;print('  client_results=%d'%len(json.load(open('$DATA/w812_read_$arm.json'))['results']))" >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prompt [0-9]+ tokens = [0-9]+ reused" | cut -c1-150 | sed 's/^/  PL /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: host: chunk setup" | sed 's/^/  PHH /' >> "$OUT"
  pm
  mark "$OUT"
}

# ---- K4 / K2：chunk 重叠（direct，不 drop） -------------------------------
for a in $ARMS; do
  case "$a" in
    K4) run_sweep K4 0 ;;
    K2) run_sweep K2 0 ;;
    RD)
      setarm RD >> "$OUT"; boot RD 1
      for n in 1 2 3; do req RD $n; done
      ;;
    RDN)
      setarm RDN >> "$OUT"; boot RDN 0     # 表已在上一条臂里被读过，cold 只在 RD 付一次
      for n in 1 2 3; do req RDN $n; done
      ;;
    *) echo "?? unknown arm $a" >> "$OUT" ;;
  esac
done

cp /tmp/w812_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
echo "== DONE $OUT"
