#!/bin/bash
# W846: 生产容器从 0.2.8p2 换成 0.2.9s1（serve 层叠 0.2.9）。失败自动切回。
set -u
C=strata166-407
OLD=strata166-407.pre-w846
NEWIMG=strata-gfx906:0.2.9s1
DATA=/home/albus/strata166/data
OUT=$DATA/w846_swap_$(date +%H%M%S).txt
ENVF=/tmp/w846_env.txt
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

# ---- 0 预检：镜像在、旧容器在、端口没被别的占 ----
docker image inspect "$NEWIMG" >/dev/null 2>&1 || { log "FATAL: $NEWIMG 不存在"; exit 1; }
docker inspect "$C" >/dev/null 2>&1 || { log "FATAL: 容器 $C 不存在"; exit 1; }
log "== preflight ok $(date +%H:%M:%S)"
docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}' > "$ENVF"
log "-- env 传入 $(wc -l < "$ENVF") 条"

# 旧容器指纹（回滚后要能对得上）
log "== 切换前: image=$(docker inspect "$C" --format '{{.Config.Image}}') started=$(docker inspect "$C" --format '{{.State.StartedAt}}') restarts=$(docker inspect "$C" --format '{{.RestartCount}}')"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('   before slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))" 2>&1 | tee -a "$OUT"

wait_health(){  # $1=秒上限
  local i
  for i in $(seq 1 "$1"); do
    if curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true'; then echo "$i"; return 0; fi
    [ $((i % 40)) -eq 0 ] && log "   wait ${i}s status=$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)"
    sleep 1
  done
  echo 0; return 1
}

rollback(){
  log "!! ROLLBACK $(date +%H:%M:%S)"
  docker rm -f "$C" >/dev/null 2>&1
  docker rename "$OLD" "$C" >/dev/null 2>&1
  docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health 600)
  log "!! 回滚完成 ready=${r}s image=$(docker inspect "$C" --format '{{.Config.Image}}')"
}

# ---- 1 停旧（温柔） ----
docker stop -t 30 "$C" >/dev/null 2>&1
for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
log "== 旧容器 status=$(docker inspect -f '{{.State.Status}}' "$C") $(date +%H:%M:%S)"

# ---- 2 换名（保留作回滚件） ----
docker rename "$C" "$OLD" || { log "FATAL: rename 失败"; exit 1; }

# ---- 3 新容器 ----
docker run -d --name "$C" \
  --restart unless-stopped --network bridge -p 8090:8090 \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  --device /dev/kfd --device /dev/dri --group-add video \
  --ipc=host --shm-size=64m --security-opt label=disable \
  --env-file "$ENVF" \
  "$NEWIMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
NEWID=$(docker inspect -f '{{.Id}}' "$C" 2>/dev/null || true)
[ -z "$NEWID" ] && { log "FATAL: 新容器没起来"; rollback; exit 1; }
log "== 新容器 id=${NEWID:0:12} $(date +%H:%M:%S)"

# ---- 4 等健康 ----
READY=$(wait_health 600)
if [ "$READY" = "0" ]; then
  log "!! 600s 未就绪 → 回滚"; docker logs --tail 30 "$C" 2>&1 >> "$OUT"; rollback; exit 1
fi
log "== health ready=${READY}s"

# ---- 5 serve 层自证：容器里跑的就是 0.2.9 ----
{
  echo "-- serve 版本自证:"
  docker exec "$C" bash -lc 'md5sum /src/serve/server.py; grep -c COALESCE_PREFILL /src/serve/server.py; grep -c PAR_COUNTERS /src/serve/server.py; ls /src/strata_control/replica_profile.py'
} >> "$OUT" 2>&1

# ---- 6 冒烟：一条 read + 一条 decode ----
B=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['requests'])" 2>/dev/null)
( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 SMOKE "$DATA/w846_read_smoke.json" 3718 1 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 SMOKE "$DATA/w846_gen_smoke.json" dec_corpus.json 128 1 ) >> "$OUT" 2>&1
A=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['requests'])" 2>/dev/null)
log "== 冒烟完成 requests ${B} -> ${A}"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('   after slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))" 2>&1 | tee -a "$OUT"

# ---- 7 门禁 ----
bash /home/albus/strata166/tmp/verify_patches.sh >> "$OUT" 2>&1
log "== gate rc=$?"
grep -aE "GATE (PASS|FAIL)" "$OUT" | tail -1 | sed 's/^/   /'
log "== DONE $OUT"
