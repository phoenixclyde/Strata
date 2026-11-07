#!/bin/bash
# W852: 7.14+5.5表(A) vs 10.1+5.7表(B)，ABBA 四臂；最后一臂落在 10.1 + 5.7 表（用户要求切）
# 每臂：重建容器（换镜像）+ 换表 + read 六档 + decode 3x200，带 mark 与 requests 增量
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
IMG714=strata-gfx906:0.2.9t2
IMG101=strata-gfx906:0.2.9r1
TBL714=/data/gfx906-rocblas-5.5.0.txt
TBL101=/data/gfx906-rocblas-5.7.0.txt
OUT=$DATA/w852_ab101_$(date +%H%M%S).txt
ENVF=/tmp/w852_env.txt
cp "$CFG" /tmp/w852_cfg_base.json
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}' > "$ENVF"
log "== preflight $(date +%H:%M:%S) env=$(wc -l < $ENVF) 条"

wait_health(){ local i; for i in $(seq 1 700); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  [ $((i % 60)) -eq 0 ] && log "   wait ${i}s status=$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)"
  sleep 1; done; echo 0; return 1; }

set_table(){ python3 - "$CFG" "$1" <<'PYX'
import json,sys
p, t = sys.argv[1], sys.argv[2]
d = json.load(open("/tmp/w852_cfg_base.json"))
e = dict(d["env"]); e["STRATA_ROCBLAS_TUNING"] = t; d["env"] = e
json.dump(d, open(p,"w"), indent=2, ensure_ascii=False)
PYX
}

run_arm(){  # $1=image $2=table $3=label
  local img=$1 tbl=$2 label=$3
  log "===== ARM $label  img=$img  table=$tbl  $(date +%H:%M:%S)"
  set_table "$tbl"
  docker stop -t 30 "$C" >/dev/null 2>&1
  for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
  docker rename "$C" "w852-$label" >/dev/null 2>&1 || docker rm -f "$C" >/dev/null 2>&1
  docker run -d --name "$C" --restart unless-stopped --network bridge -p 8090:8090 \
    -v /models:/models:ro -v /home/albus/strata166/data:/data \
    --device /dev/kfd --device /dev/dri --group-add video \
    --ipc=host --shm-size=64m --security-opt label=disable --env-file "$ENVF" \
    "$img" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
  local L0; L0=$(docker exec "$C" bash -lc "wc -l < $LOG 2>/dev/null || echo 0")
  local r; r=$(wait_health)
  [ "$r" = "0" ] && { log "  ARM $label NOT READY"; docker logs --tail 15 "$C" >> "$OUT" 2>&1; return 1; }
  log "  ready=${r}s  L0=$L0"
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'rocBLAS tuning enabled|rocBLAS version mismatch|cannot open rocBLAS' | tail -1" | sed 's/^/  TABLE /' | tee -a "$OUT"
  docker exec "$C" bash -lc "cat /opt/rocm/.info/version 2>/dev/null || echo 7.14" | sed 's/^/  ROCM /' | tee -a "$OUT"
  local B A
  B=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$label" "$DATA/w852_read_$label.json" 2575,3014,5282,5512,18980,19358 1 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
  ( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 "$label" "$DATA/w852_gen_$label.json" dec_corpus.json 200 3 ) >> "$OUT" 2>&1
  A=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
  log "  requests ${B} -> ${A}  (delta=$((A-B)))"
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'prompt [0-9]+ tokens.*read in [0-9]+ ms'" | sed 's/^/  READ /' | tee -a "$OUT"
  grep -a "MEDIAN decode_tps" "$DATA/w852_gen_$label.json" 2>/dev/null | sed 's/^/  /' | tee -a "$OUT"
  docker exec "$C" bash -lc "grep -a 'MEDIAN decode_tps' /data/strata-huihui-ud-iq4_xs.log 2>/dev/null | tail -1" | sed 's/^/  ? /' >> "$OUT" 2>&1
}

run_arm "$IMG714" "$TBL714" A
run_arm "$IMG101" "$TBL101" B
run_arm "$IMG714" "$TBL714" A2
run_arm "$IMG101" "$TBL101" B2
log "== 末臂停在 10.1 + 5.7 表（cfg 已指 /data/gfx906-rocblas-5.7.0.txt）"
bash /home/albus/strata166/tmp/verify_patches.sh >> "$OUT" 2>&1
grep -a "GATE" "$OUT" | tail -1 | sed 's/^/   /'
log "== DONE $OUT"
