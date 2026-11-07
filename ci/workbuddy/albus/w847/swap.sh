#!/bin/bash
# W847: 生产容器从 0.2.9s1(叠层) 换成 0.2.9(全树 + 组件)。失败自动回滚到 0.2.9s1。
set -u
C=strata166-407
OLD=strata166-407.pre-w847
NEWIMG=strata-gfx906:0.2.9
DATA=/home/albus/strata166/data
OUT=$DATA/w847_swap_$(date +%H%M%S).txt
ENVF=/tmp/w847_env.txt
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

docker image inspect "$NEWIMG" >/dev/null 2>&1 || { log "FATAL: $NEWIMG 不存在"; exit 1; }
log "== preflight ok $(date +%H:%M:%S) cur=$(docker inspect "$C" --format '{{.Config.Image}}') started=$(docker inspect "$C" --format '{{.State.StartedAt}}')"
docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}' > "$ENVF"

wait_health(){ local i; for i in $(seq 1 "$1"); do
    curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
    [ $((i % 40)) -eq 0 ] && log "   wait ${i}s status=$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)"
    sleep 1; done; echo 0; return 1; }

rollback(){ log "!! ROLLBACK $(date +%H:%M:%S)"
  docker rm -f "$C" >/dev/null 2>&1
  docker rename "$OLD" "$C" >/dev/null 2>&1
  docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health 600); log "!! 回滚完成 ready=${r}s image=$(docker inspect "$C" --format '{{.Config.Image}}')"; }

docker stop -t 30 "$C" >/dev/null 2>&1
for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
docker rename "$C" "$OLD" || { log "FATAL rename"; exit 1; }
log "== 旧容器已改名 $OLD $(date +%H:%M:%S)"

docker run -d --name "$C" --restart unless-stopped --network bridge -p 8090:8090 \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  --device /dev/kfd --device /dev/dri --group-add video \
  --ipc=host --shm-size=64m --security-opt label=disable --env-file "$ENVF" \
  "$NEWIMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
[ -z "$(docker inspect -f '{{.Id}}' "$C" 2>/dev/null)" ] && { log "FATAL: 新容器未起"; rollback; exit 1; }
log "== 新容器 $(docker inspect -f '{{slice .Id 0 12}}' "$C") $(date +%H:%M:%S)"

READY=$(wait_health 600)
[ "$READY" = "0" ] && { log "!! 600s 未就绪"; docker logs --tail 40 "$C" >> "$OUT" 2>&1; rollback; exit 1; }
log "== health ready=${READY}s"

echo "-- 自证 --" >> "$OUT"
docker exec "$C" bash -lc 'md5sum /src/serve/server.py /src/serve/telemetry.py; ls /src/include/strata/prefill/gdn_probe.hpp; ls /opt/strata/components/engine/' >> "$OUT" 2>&1
B=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 SMOKE "$DATA/w847_read_smoke.json" 3718 1 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 SMOKE "$DATA/w847_gen_smoke.json" dec_corpus.json 128 1 ) >> "$OUT" 2>&1
A=$(curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;print(json.load(sys.stdin)['totals']['requests'])" 2>/dev/null)
log "== 冒烟 totals.requests ${B} -> ${A}"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];h=json.load(open('/dev/stdin')) if False else None;print('   slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))" >> "$OUT" 2>&1
bash /home/albus/strata166/tmp/verify_patches.sh >> "$OUT" 2>&1
grep -a "GATE" "$OUT" | tail -1 | sed 's/^/   /'
log "== DONE $OUT"
