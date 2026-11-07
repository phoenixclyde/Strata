#!/bin/bash
# W857 · 一次停服做两件事（§6.5 权重④ 战线集中）
#   A 臂：banner 二进制 + STRATA_PREFILL_TIMING=1        → R17 层分布 + 基线相位
#   B 臂：同二进制 + TIMING=1 + STRATA_PREFILL_RING=8    → R15 负对照：ring 钉在 STAGE(8)
#   收尾：exe 回 0.1.55g、去掉 TIMING/RING，重启回生产
# 判据：只用 rep0；日志用启动前行数做 mark；banner 行只在 prefill 时打印。
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
BANNER_HOST=$DATA/bin/strata-0.1.55-banner
BANNER_BIN=/data/bin/strata-0.1.55-banner
OUT=$DATA/w857_$(date +%H%M%S).txt
cp "$CFG" /tmp/w857_cfg_base.json
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

wait_health(){ local i; for i in $(seq 1 700); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }

restart(){ docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1; }

restore(){
  log "!! RESTORE $(date +%H:%M:%S)"
  cp /tmp/w857_cfg_base.json "$CFG"
  restart
  local r; r=$(wait_health)
  log "!! 恢复 ready=${r}s env_n=$(python3 -c "import json;print(len(json.load(open('$CFG'))['env']))") exe=$(python3 -c "import json;print(json.load(open('$CFG'))['exe'])")"
  log "!! 容器内 exe md5: $(docker exec "$C" md5sum /data/bin/strata-0.1.55g 2>/dev/null | cut -d' ' -f1)"
}
trap restore EXIT

setenv(){  # setenv key value
  python3 - "$CFG" "$1" "$2" <<'PYX'
import json, sys
p, k, v = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open("/tmp/w857_cfg_base.json"))
e = dict(d["env"])
if v == "__DEL__":
    e.pop(k, None)
else:
    e[k] = v
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  env_n =", len(e))
PYX
}

run_arm(){ # run_arm <tag>
  local tag=$1
  L0=$(docker exec "$C" bash -lc "wc -l < $LOG")
  restart
  local r; r=$(wait_health); log "  ready=${r}s  L0=$L0"
  [ "$r" = "0" ] && { log "  NOT READY"; return 1; }
  for sz in 300 1300 2575; do
    ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$tag" "$DATA/w857_${tag}_read_$sz.json" "$sz" 1 kl_pool2.json 300 2 ) >> "$OUT" 2>&1
  done
  log "  --- banner / 相位（mark 之后） ---"
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'prompt experts:|prefill timing:' | tail -9" | tee -a "$OUT"
}

log "== W857 开始 $(date +%H:%M:%S)"
cp -f /home/albus/strata166/gfx-mmq-build/strata "$BANNER_HOST" || { log "copy banner 失败"; exit 1; }
chmod +x "$BANNER_HOST"
log "  banner md5: $(md5sum "$BANNER_HOST" | cut -d' ' -f1)"

log "== ARM A banner + TIMING，ring 默认"
python3 - "$CFG" <<'PYX' | tee -a "$OUT"
import json, sys
p = sys.argv[1]
d = json.load(open("/tmp/w857_cfg_base.json"))
d["exe"] = "/data/bin/strata-0.1.55-banner"
e = dict(d["env"]); e["STRATA_PREFILL_TIMING"] = "1"
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("  exe=banner env_n =", len(e))
PYX
run_arm A

log "== ARM B banner + TIMING + RING=8（负对照）"
setenv STRATA_PREFILL_RING 8 | tee -a "$OUT"
run_arm B

log "== DONE $(date +%H:%M:%S)"
