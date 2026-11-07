#!/bin/bash
# W851b: 重跑 4 桶 vs 6 桶。修 W851 的 bug：配置里的 STRATA_ROCBLAS_TUNING 必须是**容器内路径** /data/...
# 每臂带 mark（启动前日志行数），只用 mark 之后的新行判"表是否真加载"。
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
OLD=/data/gfx906-rocblas-5.5.0.txt
NEW=/data/gfx906-rocblas-5.5.0-6b.txt
OUT=$DATA/w851_abtbl2_$(date +%H%M%S).txt
cp "$CFG" /tmp/w851b_cfg_base.json
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

wait_health(){ local i; for i in $(seq 1 600); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }

restore(){ log "!! RESTORE $(date +%H:%M:%S)"
  cp /tmp/w851b_cfg_base.json "$CFG"
  docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health); log "!! 恢复 ready=${r}s cfg_table=$(python3 -c "import json;print(json.load(open('$CFG'))['env']['STRATA_ROCBLAS_TUNING'])")"; }
trap restore EXIT

set_table(){ python3 - "$CFG" "$1" <<'PYX'
import json,sys
p, t = sys.argv[1], sys.argv[2]
d = json.load(open("/tmp/w851b_cfg_base.json"))
e = dict(d["env"]); e["STRATA_ROCBLAS_TUNING"] = t; d["env"] = e
json.dump(d, open(p,"w"), indent=2, ensure_ascii=False)
print("  cfg table =", t)
PYX
}

arm(){ # $1=容器内表路径 $2=label
  local tbl=$1 label=$2
  log "===== ARM $label  $tbl  $(date +%H:%M:%S)"
  set_table "$tbl" | tee -a "$OUT"
  local L0; L0=$(docker exec "$C" bash -lc "wc -l < $LOG")
  docker stop -t 30 "$C" >/dev/null 2>&1
  for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
  docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health)
  [ "$r" = "0" ] && { log "  ARM $label NOT READY"; return 1; }
  log "  ready=${r}s  (log mark L0=$L0)"
  # 只认 mark 之后新出现的行
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'rocBLAS tuning enabled|rocBLAS version mismatch|cannot open rocBLAS' | tail -1" | sed 's/^/  TABLE /' | tee -a "$OUT"
  local B A
  B=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$label" "$DATA/w851b_read_$label.json" 300,700,1300 2 kl_pool2.json 120 2 ) >> "$OUT" 2>&1
  A=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
  log "  requests ${B} -> ${A}  (delta=$((A-B)))"
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'prompt [0-9]+ tokens.*read in [0-9]+ ms'" | sed 's/^/  READ /' | tee -a "$OUT"
}

arm "$OLD" A
arm "$NEW" B
arm "$OLD" A2
arm "$NEW" B2
log "== DONE $OUT"
