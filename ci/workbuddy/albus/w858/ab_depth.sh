#!/bin/bash
# W858 补充臂：routed stream + DEPTH=256（只改 env，不重建）
#   目的：把 A/B 里的 1K 回退归因分清——是"drop 逻辑没用"还是"depth=16 把预取压浅了"。
#   若 256 下 1K 回到基线、且 wait copy 回落 ⇒ depth gate 是元凶，drop 逻辑本身无害（但也无益）。
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
LOG=/data/strata-huihui-ud-iq4_xs.log
OUT=$DATA/w858_depth_$(date +%H%M%S).txt
log(){ echo "$@" | tee -a "$OUT"; }
wait_health(){ local i; for i in $(seq 1 900); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
  sleep 1; done; echo 0; return 1; }
restart(){ docker stop -t 30 "$C" >/dev/null 2>&1; docker start "$C" >/dev/null 2>&1; }

restore(){
  log "!! RESTORE $(date +%H:%M:%S)"
  python3 - "$CFG" <<'PYX'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["exe"] = "/data/bin/strata-0.1.55g"
e = dict(d["env"])
for k in ("STRATA_PREFILL_ROUTED_STREAM", "STRATA_PREFILL_ROUTED_STREAM_DEPTH", "STRATA_PREFILL_TIMING"):
    e.pop(k, None)
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("    restored exe=%s env_n=%d" % (d["exe"], len(e)))
PYX
  restart
  local r; r=$(wait_health)
  log "!! ready=${r}s exe=$(python3 -c "import json;print(json.load(open('$CFG'))['exe'])") env_n=$(python3 -c "import json;print(len(json.load(open('$CFG'))['env']))")"
  log "!! md5=$(docker exec "$C" md5sum /data/bin/strata-0.1.55g 2>/dev/null | cut -d' ' -f1)"
  log "!! health=$(curl -s --max-time 3 http://127.0.0.1:8090/health | head -c 80)"
}
trap restore EXIT

log "== W858 depth=256 臂 $(date +%H:%M:%S)"
python3 - "$CFG" <<'PYX' | tee -a "$OUT"
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["exe"] = "/data/bin/strata-0.1.55-routed"
e = dict(d["env"])
e["STRATA_PREFILL_TIMING"] = "1"
e["STRATA_PREFILL_ROUTED_STREAM"] = "1"
e["STRATA_PREFILL_ROUTED_STREAM_DEPTH"] = "256"
d["env"] = e
json.dump(d, open(p, "w"), indent=2, ensure_ascii=False)
print("    exe=routed env_n=%d depth=256" % len(e))
PYX

L0=$(docker exec "$C" bash -lc "wc -l < $LOG")
restart
r=$(wait_health); log "  ready=${r}s L0=$L0"
[ "$r" = "0" ] && { log "  NOT READY"; exit 1; }
for sz in 300 1300 2575 10000; do
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 B256 "$DATA/w858_B256_read_$sz.json" "$sz" 1 kl_pool2.json 3300 2 ) >> "$OUT" 2>&1
done
log "  --- 引擎侧 ---"
docker exec "$C" bash -lc "sed -n '$((L0+1)),\$p' $LOG | grep -aE 'prompt [0-9]+ tokens|ROUTED_STREAM|prefill timing:' | tail -20" | tee -a "$OUT"
log "== DONE $(date +%H:%M:%S)"
