#!/bin/bash
# W853/M5: 用 STRATA_PREFILL_TIMING 把一次 prefill 拆成相位（不停服以外唯一做法：只加一个 env + 重启）
# 目的：W851 证明 dense GEMM 只占 0.68%，要找出剩下 99% 花在哪
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
OUT=$DATA/w853_m5_$(date +%H%M%S).txt
cp "$CFG" /tmp/w853_cfg_base.json
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

wait_health(){ local i; for i in $(seq 1 700); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }

restore(){
  log "!! RESTORE $(date +%H:%M:%S)"
  cp /tmp/w853_cfg_base.json "$CFG"
  docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health); log "!! 恢复 ready=${r}s env_n=$(python3 -c "import json;print(len(json.load(open('$CFG'))['env']))")"
}
trap restore EXIT

log "== 加 STRATA_PREFILL_TIMING=1 并重启 $(date +%H:%M:%S)"
python3 - "$CFG" <<'PYX' | tee -a "$OUT"
import json, sys
p = sys.argv[1]
d = json.load(open("/tmp/w853_cfg_base.json"))
e = dict(d["env"]); e["STRATA_PREFILL_TIMING"] = "1"; d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  env_n =", len(e), " added STRATA_PREFILL_TIMING=1")
PYX

L0=$(docker exec "$C" bash -lc "wc -l < $LOG")
docker stop -t 30 "$C" >/dev/null 2>&1
for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
docker start "$C" >/dev/null 2>&1
r=$(wait_health); log "  ready=${r}s  L0=$L0"
[ "$r" = "0" ] && { log "  NOT READY"; exit 1; }

# 只发三档：小（落 256/512 桶）、中、长，方便对比相位结构
for sz in 300 1300 2575; do
  log "  --- 发 prompt ~${sz} tok"
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 M5 "$DATA/w853_m5_read_$sz.json" "$sz" 1 kl_pool2.json 300 2 ) >> "$OUT" 2>&1
done

log "== 相位日志（mark 之后） =="
docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aiE 'prefill.*(phase|timing)|phase .*ms|prefill timing' | tail -60" | tee -a "$OUT"
log "== 原始行样本 =="
docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -a 'read in ' | tail -5" | tee -a "$OUT"
log "== DONE $OUT"
