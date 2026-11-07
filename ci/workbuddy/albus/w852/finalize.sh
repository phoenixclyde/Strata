#!/bin/bash
# W852: 把 10.1 从"候选名 r1"转正为正式 tag，并用正式名重建生产容器
set -u
C=strata166-407
DATA=/home/albus/strata166/data
CFG=$DATA/strata-huihui-ud-iq4_xs.json
OFFICIAL=strata-gfx906:0.2.9-101
ENVF=/tmp/w852b_env.txt
OUT=$DATA/w852_finalize_$(date +%H%M%S).txt
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

docker tag strata-gfx906:0.2.9r1 "$OFFICIAL" || { log "FATAL tag"; exit 1; }
log "== tag 完成: $OFFICIAL = $(docker image inspect "$OFFICIAL" --format '{{.Id}}' | cut -c1-19)"
docker images strata-gfx906 --format '  {{.Tag}}  {{.Size}}  {{.Id}}' | sed 's/^/ /' | head -8

docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}' > "$ENVF"
docker stop -t 30 "$C" >/dev/null 2>&1
for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
docker rename "$C" "strata166-407.pre-w852" >/dev/null 2>&1 || docker rm -f "$C" >/dev/null 2>&1
log "== 旧容器改名 pre-w852，用正式 tag 重建"

docker run -d --name "$C" --restart unless-stopped --network bridge -p 8090:8090 \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  --device /dev/kfd --device /dev/dri --group-add video \
  --ipc=host --shm-size=64m --security-opt label=disable --env-file "$ENVF" \
  "$OFFICIAL" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1

ok=0
for i in $(seq 1 700); do
  curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { ok=$i; break; }
  [ $((i % 60)) -eq 0 ] && log "   wait ${i}s"
  sleep 1
done
if [ "$ok" = "0" ]; then log "!! NOT READY，回滚"; docker rm -f "$C"; docker rename strata166-407.pre-w852 "$C"; docker start "$C"; exit 1; fi
log "== health ready=${ok}s"

docker exec "$C" bash -lc 'echo -n "  rocm: "; cat /opt/rocm/.info/version; echo -n "  table: "; grep -c "^f16o" /data/gfx906-rocblas-5.7.0.txt' | tee -a "$OUT"
curl -s --max-time 6 http://127.0.0.1:8090/metrics | python3 -c "import sys,json;e=json.load(sys.stdin)['engine'];print('  slots=%d vram_free=%d pcie=%s'%(e['expert_slots'],e['vram_free_mib'],e.get('pcie_frac')))" | tee -a "$OUT"
bash /home/albus/strata166/tmp/verify_patches.sh >> "$OUT" 2>&1
grep -a "GATE\|img=" "$OUT" | tail -2 | sed 's/^/   /'
log "== DONE $OUT"
