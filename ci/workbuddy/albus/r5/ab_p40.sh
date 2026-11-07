#!/bin/bash
# W810 / P138：`--ple-io` 三臂 + `--ple-row-cache` 两档 —— 提示侧最大的一块可动项
#
# 机理（源码逐字，全部在本轮复核过）：
#   * 表 = **320,001,536 行 × 90 B = 26.8 GiB**（`include/strata/ngram/ple_reader.hpp:5`），
#     "is never held in RAM: every row comes from an unbuffered 4 KiB read"。
#   * 一个 token 要 **16 行、落在 16 个不同的 4 KiB 页**上，且 16 行都取决于 token 本身，
#     "the only time to hide them is the embedding plus layer 0"（同文件:5-14）。
#   * `prefill` 相位表（`src/prefill/prefill.cpp:2500-2504`）的口径：相邻两个 event 之间、落在**前一个**相位上
#     => `ple` 这一项 = **GPU 流等主机把这一块的 16×N 行读回来的空转**，不是 GPU 计算。
#   * 生产是缺省 `direct`（`generate.cpp:480`），且引擎**不会自己换**（:4066-4089，只有 STRATA_PLE_AUTO_MMAP=1 才换）。
#   * `--ple-io ram` = mmap + MADV_WILLNEED + 16 线程全表 touch + mlock（`src/kernels/ngram.cpp:386-410`）。
#     本容器 `ulimit -l` = **8 MB** => mlock 必然失败、只警告，页面"faulted in but may be reclaimed"（上游 INTEL.md:723 同一现象）。
#   * `--ple-io mmap` = 纯映射，不走 O_DIRECT；**但 Linux 下 decode 的 `gather()` 没有预取**
#     （`ngram.cpp:682-684` 的 `PrefetchVirtualMemory` 在 `#if defined(_WIN32)` 里）=> 16 次串行缺页。
#     `ngram.cpp:640-658` 自己量过：**2.10-2.61 ms/token**（Windows 上做了补救，Linux 上没有）。
#     上游 DETAILS.md:2296 另有：SATA 盘上 mmap 2.1K rows/s 对 direct 14.4K（#2040）。
#   * 本机盘 = **Fanxiang S100Pro（SATA）**；启动探针 direct = **34.5K rows/s**（阈值 15K，判 "fine"）。
#
# 臂：A=生产 A2=A 重复（规则 X） B=mmap C=ram D=row-cache 4M(380MB) E=row-cache 0（负对照）
# 每臂：read 1500/3000/6000 × 2 次（fresh 文本，跨臂同一份文本）+ 解码 3×128（查相位迁移）
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
DATA=/home/albus/strata166/data
LOG=$DATA/strata-huihui-ud-iq4_xs.log
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=$DATA/w810_pleio_$STAMP.txt
SIZES=1500,3000,6000
REPS=2
ARMS=${*:-"A A2 B C D E"}

cp "$CFG" /tmp/w810_prod.json
restore_cfg() {
  cp /tmp/w810_prod.json "$CFG" 2>/dev/null
  docker restart strata166-407 >/dev/null 2>&1
  for i in $(seq 1 400); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && break; sleep 1; done
  echo "  trap-restored (any exit path)" >> "$OUT"
}
trap restore_cfg EXIT

echo "# W810 P138 --ple-io sweep $STAMP sizes=$SIZES reps=$REPS arms='$ARMS'" > "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));print('  start env_n=%d args_n=%d'%(len(d['env']),len(d['args'])))" >> "$OUT"
echo "  disk=$(lsblk -dno MODEL /dev/sda 2>/dev/null | tr -d ' ')" >> "$OUT"
free -m | sed -n 1,2p | sed 's/^/  MEM /' >> "$OUT"

setarm() {   # $1=arm
  python3 - "$CFG" "$1" <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
SPEC = {"A": (None, None), "A2": (None, None), "B": ("mmap", None),
        "C": ("ram", None), "D": (None, "4194304"), "E": (None, "0")}
io_mode, rowcache = SPEC[arm]
base = json.load(open("/tmp/w810_prod.json"))
e = dict(base.get("env") or {})
e["STRATA_PREFILL_TIMING"] = "1"      # 相位表（规则 Z 要用）
e["STRATA_DECODE_TIMING"] = "1"       # 解码结构（查相位迁移）
a = list(base.get("args") or [])
for k in ("--ple-io", "--ple-row-cache"):
    while k in a:
        i = a.index(k); del a[i:i + 2]
if io_mode is not None:
    a += ["--ple-io", io_mode]
if rowcache is not None:
    a += ["--ple-row-cache", rowcache]
d = dict(base)
d["env"] = e
d["args"] = a
assert set(d.keys()) == set(base.keys()), "丢了顶层键"
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  CFGCHECK keys=%d env_n=%d args_n=%d ple_io=%s row_cache=%s"
      % (len(d), len(e), len(a), io_mode or "direct(缺省)", rowcache or "1048576(缺省)"))
PY
}

run() {   # $1=arm
  local arm=$1
  setarm "$arm" >> "$OUT"
  local t0 t1 ok=0
  t0=$(date +%s)
  docker restart strata166-407 >/dev/null 2>&1
  # ram 臂要 touch 26.8 GiB 全表，给到 900 s
  for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  t1=$(date +%s)
  mark "$OUT"
  echo "=== ARM $arm ready=${ok}s start_wall=$((t1 - t0))s" >> "$OUT"
  # 自证 1：引擎命令行里的 --ple-io / --ple-row-cache
  grep -a "engine started:" "$LOG" | tail -1 | grep -oE "\-\-ple-io [a-z]+|--ple-row-cache [0-9]+" | tr '\n' ' ' | sed 's/^/  VW /' >> "$OUT"
  echo >> "$OUT"
  # 自证 2：本次启动的模式证据（direct=探针行；ram=载入行；mmap=两者皆无）
  docker logs --since 20m strata166-407 2>&1 | grep -a -E "PLE direct read probe|PLE table .* in [0-9.]+ s|mlock failed" | tail -4 | sed 's/^/  MODE /' >> "$OUT"
  if [ "$ok" = "0" ]; then echo "!! ABORT: engine never became ready in arm $arm" >> "$OUT"; echo "ABORT"; exit 1; fi
  python3 mt_read.py 8090 "$arm" "$DATA/w810_read_$arm.json" "$SIZES" "$REPS" kl_pool.json >> "$OUT" 2>&1
  if [ ! -f "$DATA/w810_read_$arm.json" ]; then
    echo "!! ABORT: client produced no JSON for arm $arm" >> "$OUT"; echo "ABORT client"; exit 1
  fi
  local n
  n=$(python3 -c "import json;print(len(json.load(open('$DATA/w810_read_$arm.json'))['results']))" 2>/dev/null)
  echo "  client_results=${n:-0} (want $(( $(echo "$SIZES" | tr ',' '\n' | wc -l) * REPS )))" >> "$OUT"
  # 真值：prompt 行 + 相位表全文
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prompt [0-9]+ tokens = [0-9]+ reused" | cut -c1-150 | sed 's/^/  PL /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: [0-9]+ tokens, GPU timeline" | sed 's/^/  PH /' >> "$OUT"
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a -E "prefill timing: host: chunk setup" | sed 's/^/  PHH /' >> "$OUT"
  # 解码（相位迁移守卫）
  python3 mt_gen.py 8090 "$arm" "$DATA/w810_gen_$arm.json" dec_corpus.json 128 3 >> "$OUT" 2>&1
  tail -n +$(( $(cat /tmp/.a9_mark) + 1 )) "$LOG" | grep -a "strata decode timing" | sed 's/^/  DT /' >> "$OUT"
  # 内存占用（ram 臂必须能看到 +26.8 GiB）
  docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && grep -E "^(VmRSS|RssAnon|RssFile)" /proc/$p/status' 2>/dev/null | tr '\n' ' ' | sed 's/^/  RSS /' >> "$OUT"
  echo >> "$OUT"
  free -m | sed -n 2p | sed 's/^/  MEM /' >> "$OUT"
}

for a in $ARMS; do run "$a"; done

cp /tmp/w810_prod.json "$CFG"
docker restart strata166-407 >/dev/null 2>&1
for i in $(seq 1 900); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "restored ${i}s" >> "$OUT"; break; }; sleep 1; done
python3 -c "import json;d=json.load(open('$CFG'));print('final env_n=%d args_n=%d ple_io=%s'%(len(d['env']),len(d['args']),'--ple-io' in d['args']))" >> "$OUT"
echo "== DONE $OUT"
