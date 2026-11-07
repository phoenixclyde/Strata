#!/bin/bash
# W858 A 线 A/B：routed stream（上游 #4283，已 cherry-pick 到 gfx906/routed-stream）
#   A  生产 0.1.55g + TIMING=1                     ← 基线
#   B  0.1.55-routed + TIMING=1 + ROUTED_STREAM=1  ← 处理臂
#   A2 生产 0.1.55g + TIMING=1                     ← 复本（控漂移）
# 四档 prompt（约 250 / 1170 / 1920 / 8000 tok），每档 2 预热 + 1 实测
# 纪律：只用每档最后一条（预热不入表）；每臂比 /metrics requests 增量（防外来请求）
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
OUT=$DATA/w858_ab_$(date +%H%M%S).txt
SRC_BIN=/home/albus/strata166/gfx-routed-build/strata
log(){ echo "$@" | tee -a "$OUT"; }

wait_health(){ local i; for i in $(seq 1 900); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }

restart(){ docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1; }

reqs(){ curl -s --max-time 5 http://127.0.0.1:8090/metrics 2>/dev/null | awk '/^requests/ {print $2}' | head -1; }

setkv(){  # setkv exe|env <key> <value>   —— 改的是**当前**配置，不是基线（W857 的 bug 就在这）
  python3 - "$CFG" "$1" "$2" <<'PYX'
import json, sys
p, kind, v = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(p))
if kind == "exe":
    d["exe"] = v
else:
    e = dict(d["env"]); e[kind] = v; d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("    cfg: exe=%s env_n=%d" % (d["exe"], len(d["env"])))
PYX
}
delkv(){ python3 - "$CFG" "$1" <<'PYX'
import json, sys
p, k = sys.argv[1], sys.argv[2]
d = json.load(open(p)); e = dict(d["env"]); e.pop(k, None); d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("    cfg: del %s -> env_n=%d" % (k, len(e)))
PYX
}

restore(){
  log "!! RESTORE $(date +%H:%M:%S)"
  cp /tmp/w858_cfg_base.json "$CFG"
  restart
  local r; r=$(wait_health)
  log "!! ready=${r}s exe=$(python3 -c "import json;print(json.load(open('$CFG'))['exe'])") env_n=$(python3 -c "import json;print(len(json.load(open('$CFG'))['env']))")"
  log "!! md5=$(docker exec "$C" md5sum /data/bin/strata-0.1.55g 2>/dev/null | cut -d' ' -f1)"
  log "!! health=$(curl -s --max-time 3 http://127.0.0.1:8090/health | head -c 90)"
}
trap restore EXIT

run_arm(){  # run_arm <tag> <start_idx>
  local tag=$1 start=$2
  local L0=$(docker exec "$C" bash -lc "wc -l < $LOG")
  local R0=$(reqs)
  restart
  local r; r=$(wait_health); log "  ready=${r}s L0=$L0 req0=$R0"
  [ "$r" = "0" ] && { log "  NOT READY"; return 1; }
  for sz in 300 1300 2575 10000; do
    ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$tag" "$DATA/w858_${tag}_read_$sz.json" "$sz" 1 kl_pool2.json "$start" 2 ) >> "$OUT" 2>&1
  done
  local R1=$(reqs); log "  req_delta=$((R1-R0)) (期望 12)"
  log "  --- 引擎侧（mark 之后）---"
  docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'prompt [0-9]+ tokens|prompt experts:|ROUTED_STREAM|prefill timing:' | tail -24" | tee -a "$OUT"
}

log "== W858 A/B 开始 $(date +%H:%M:%S)"
cp "$CFG" /tmp/w858_cfg_base.json
cp -f "$SRC_BIN" "$DATA/bin/strata-0.1.55-routed" || { log "copy routed 失败"; exit 1; }
chmod +x "$DATA/bin/strata-0.1.55-routed"
log "  routed md5: $(md5sum "$DATA/bin/strata-0.1.55-routed" | cut -d' ' -f1)  size=$(stat -c%s "$DATA/bin/strata-0.1.55-routed")"

log "== ARM A  生产基线"
setkv exe /data/bin/strata-0.1.55g | tee -a "$OUT"
setkv STRATA_PREFILL_TIMING 1 | tee -a "$OUT"
delkv STRATA_PREFILL_ROUTED_STREAM | tee -a "$OUT"
run_arm A 300

log "== ARM B  routed stream"
setkv exe /data/bin/strata-0.1.55-routed | tee -a "$OUT"
setkv STRATA_PREFILL_ROUTED_STREAM 1 | tee -a "$OUT"
run_arm B 1300

log "== ARM A2 生产基线（复本）"
setkv exe /data/bin/strata-0.1.55g | tee -a "$OUT"
delkv STRATA_PREFILL_ROUTED_STREAM | tee -a "$OUT"
run_arm A2 2300

log "== DONE $(date +%H:%M:%S)"
