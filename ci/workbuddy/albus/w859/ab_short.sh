#!/bin/bash
# W859-b：R4 的决定性复测
#   上一轮的 A/B 是空转：gemm.cu:1369 `T > max_t → return false`，默认 max_t=256，
#   而我们最短的整段 prompt 是 ~290 token ⇒ 开关从未生效。
#   这一轮：加 150/250 token 短档（R4 的真靶心），并把 MAX_T 抬到 1024。
#   两臂：A(生产) 与 B(mmvq + MAX_T=1024)，同尺寸同顺序。
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
OUT=$DATA/w859_short_$(date +%H%M%S).txt
log(){ echo "$@" | tee -a "$OUT"; }
wait_health(){ local i; for i in $(seq 1 900); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }
restart(){ docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1; }
setkv(){ python3 - "$CFG" "$1" "$2" <<'PYX'
import json, sys
p, kind, v = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(p))
if kind == "exe":
    d["exe"] = v
else:
    e = dict(d["env"]); e[kind] = v; d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("    cfg exe=%s env_n=%d" % (d["exe"], len(d["env"])))
PYX
}
delkv(){ python3 - "$CFG" "$1" <<'PYX'
import json, sys
p, k = sys.argv[1], sys.argv[2]
d = json.load(open(p)); e = dict(d["env"]); e.pop(k, None); d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("    cfg del %s env_n=%d" % (k, len(e)))
PYX
}
restore(){
  log "!! RESTORE $(date +%H:%M:%S)"
  cp /tmp/w859b_cfg_base.json "$CFG"
  restart
  local r; r=$(wait_health)
  log "!! ready=${r}s exe=$(python3 -c "import json;print(json.load(open('$CFG'))['exe'])") env_n=$(python3 -c "import json;print(len(json.load(open('$CFG'))['env']))")"
  log "!! md5=$(docker exec "$C" md5sum /data/bin/strata-0.1.55g 2>/dev/null | cut -d' ' -f1)"
}
trap restore EXIT
run_arm(){ local tag=$1 start=$2
  local L0=$(docker exec "$C" bash -lc "wc -l < $LOG")
  restart
  local r; r=$(wait_health); log "  ready=${r}s L0=$L0"
  [ "$r" = "0" ] && { log "  NOT READY"; return 1; }
  for sz in 450 800 1300 2575 10000; do
    ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$tag" "$DATA/w859s_${tag}_read_$sz.json" "$sz" 1 kl_pool2.json "$start" 2 ) >> "$OUT" 2>&1
  done
  log "  --- 引擎侧 ---"
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'prompt [0-9]+ tokens|prefill timing: [0-9]+' | tail -20" | tee -a "$OUT"
}
log "== W859-b 短档复测 $(date +%H:%M:%S)"
cp "$CFG" /tmp/w859b_cfg_base.json
log "== ARM A 生产"
setkv exe /data/bin/strata-0.1.55g | tee -a "$OUT"
setkv STRATA_PREFILL_TIMING 1 | tee -a "$OUT"
delkv STRATA_PF_MMVQ | tee -a "$OUT"
run_arm A 500
log "== ARM B mmvq MAX_T=1024"
setkv exe /data/bin/strata-0.1.55-mmvq | tee -a "$OUT"
setkv STRATA_PF_MMVQ 1 | tee -a "$OUT"
setkv STRATA_PF_MMVQ_MAX_T 1024 | tee -a "$OUT"
run_arm B 1500
log "== DONE $(date +%H:%M:%S)"
