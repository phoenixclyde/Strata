#!/bin/bash
# W802-A（P1 显存安全线）：--vram-reserve-mib 768 vs 832
#   现役请求期最低 506 MiB，已低于引擎阈值 512（#2065：驱动换页 => decode 掉到个位数 tok/s）
#   判据：M prompt_ms 不劣于 -0.5%，且请求期不再出现 "only N MiB of VRAM free" 告警
set -u
cd /home/albus/strata166/tmp || exit 1
. ./lib_a9.sh
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=/home/albus/strata166/data/w802a_vram_$STAMP.txt
FLAG=--vram-reserve-mib
cp "$CFG" "$CFG.bak_w802a_$STAMP"
echo "# W802a vram-reserve 768 vs 832  $STAMP  order=768 832 832 768  每臂 M x2" > "$OUT"

setv() {
  python3 - "$CFG" "$1" "$FLAG" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, val, flag = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(cfg)); a = list(d.get("args") or [])
out, i = [], 0
while i < len(a):
    if a[i] == flag:
        if i + 1 < len(a) and not a[i + 1].startswith("-"): i += 2
        else: i += 1
        continue
    out.append(a[i]); i += 1
out += [flag, val]
d["args"] = out
json.dump(d, open(cfg, "w"), indent=2, ensure_ascii=False)
print("  setv reserve=%s" % val)
PY
}

run() {
  local val=$1 rep=$2
  setv "$val"
  docker restart strata166-407 >/dev/null 2>&1
  local ok=0
  for i in $(seq 1 300); do curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { ok=$i; break; }; sleep 1; done
  mark "$OUT"
  echo "=== ARM reserve=$val rep $rep ready=${ok}s" >> "$OUT"
  snap "$OUT"
  docker exec strata166-407 bash -lc 'p=$(pgrep -f "build-906/strata --serve" | head -1); [ -n "$p" ] && tr "\0" "\n" < /proc/$p/environ | grep -c "^STRATA_"' 2>/dev/null | sed 's/^/  ENVCHECK got=/;s/$/ (want 11)/' >> "$OUT"
  python3 w776_bench.py M 2 >> "$OUT" 2>&1
  slice "$OUT" "only [0-9]+ MiB of VRAM free"
}

run 768 1
run 832 1
run 832 2
run 768 2

echo "== DONE $OUT"
