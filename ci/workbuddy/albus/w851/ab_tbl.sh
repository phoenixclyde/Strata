#!/bin/bash
# W851: rocBLAS 表 4 桶 vs 6 桶（补 256/512）—— 只改 STRATA_ROCBLAS_TUNING，不动镜像/二进制
# 判据：短 prompt（落 256/512 桶）的 read 应下降；1300 tok（落 1024 桶）应不变（对照）
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
OLD=$DATA/gfx906-rocblas-5.5.0.txt
NEW=$DATA/gfx906-rocblas-5.5.0-6b.txt
OUT=$DATA/w851_abtbl_$(date +%H%M%S).txt
cp "$CFG" /tmp/w851_cfg_base.json
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

wait_health(){ local i; for i in $(seq 1 600); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }

restore(){ log "!! RESTORE $(date +%H:%M:%S)"
  cp /tmp/w851_cfg_base.json "$CFG"
  docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health); log "!! 恢复 ready=${r}s table=$(python3 -c "import json;print(json.load(open('$CFG'))['env']['STRATA_ROCBLAS_TUNING'])")"; }
trap restore EXIT

set_table(){ python3 - "$CFG" "$1" <<'PYX'
import json,sys
p, t = sys.argv[1], sys.argv[2]
d = json.load(open("/tmp/w851_cfg_base.json"))
e = dict(d["env"]); e["STRATA_ROCBLAS_TUNING"] = t; d["env"] = e
json.dump(d, open(p,"w"), indent=2, ensure_ascii=False)
print("  table =", t, " env_n =", len(e))
PYX
}

arm(){ # $1=table file $2=label
  local tbl=$1 label=$2
  log "===== ARM $label  table=$(basename "$tbl")  $(date +%H:%M:%S)"
  set_table "$tbl" | tee -a "$OUT"
  docker stop -t 30 "$C" >/dev/null 2>&1
  for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
  docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health)
  [ "$r" = "0" ] && { log "  ARM $label NOT READY"; return 1; }
  log "  ready=${r}s"
  docker exec "$C" bash -lc "grep -a 'rocBLAS tuning enabled' $LOG | tail -1" | sed 's/^/  /' | tee -a "$OUT"
  local B A
  B=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$label" "$DATA/w851_read_$label.json" 300,700,1300 2 kl_pool2.json 120 2 ) >> "$OUT" 2>&1
  A=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
  log "  requests ${B} -> ${A}"
  docker exec "$C" bash -lc "grep -aE 'prompt [0-9]+ tokens.*read in [0-9]+ ms' $LOG | tail -6" | sed 's/^/  READ /' | tee -a "$OUT"
}

arm "$OLD" A
arm "$NEW" B
arm "$OLD" A2
arm "$NEW" B2
log "== DONE $OUT"
