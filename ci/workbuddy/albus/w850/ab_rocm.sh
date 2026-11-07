#!/bin/bash
# W850: ROCm A/B —— 7.14（生产）vs 10.1（候选）。同一二进制、同一配置，只换镜像。
# 三臂 A(7.14) / B(10.1) / A2(7.14) 交错，判读用 read 六档 + decode 3x200 中位；任何失败恢复生产 0.2.9t2。
set -u
C=strata166-407
DATA=/home/albus/strata166/data
OUT=$DATA/w850_rocm_$(date +%H%M%S).txt
ENVF=/tmp/w850_env.txt
PROD=strata-gfx906:0.2.9t2
: > "$OUT"
log(){ echo "$@" | tee -a "$OUT"; }

docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}' > "$ENVF"
log "== preflight $(date +%H:%M:%S) cur=$(docker inspect "$C" --format '{{.Config.Image}}')"

wait_health(){ local i; for i in $(seq 1 "${1:-600}"); do
    curl -s --max-time 2 http://127.0.0.1:8090/health 2>/dev/null | grep -q '"loaded": *true' && { echo "$i"; return 0; }
    [ $((i % 60)) -eq 0 ] && log "   wait ${i}s status=$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)"
    sleep 1; done; echo 0; return 1; }

restore_prod(){
  log "!! RESTORE 生产 $PROD $(date +%H:%M:%S)"
  docker rm -f "$C" >/dev/null 2>&1
  docker rename "$1" "$C" >/dev/null 2>&1 || true
  docker start "$C" >/dev/null 2>&1
  local r; r=$(wait_health 600); log "!! 生产恢复 ready=${r}s image=$(docker inspect "$C" --format '{{.Config.Image}}')"
}

arm(){  # $1=image $2=label
  local img=$1 label=$2 old="strata166-407.arm-$2"
  log "===== ARM $label  image=$img  $(date +%H:%M:%S)"
  docker stop -t 30 "$C" >/dev/null 2>&1
  for i in $(seq 1 90); do [ "$(docker inspect -f '{{.State.Status}}' "$C")" = "exited" ] && break; sleep 1; done
  docker rename "$C" "$old" || { log "FATAL rename"; return 1; }
  docker run -d --name "$C" --restart unless-stopped --network bridge -p 8090:8090 \
    -v /models:/models:ro -v /home/albus/strata166/data:/data \
    --device /dev/kfd --device /dev/dri --group-add video \
    --ipc=host --shm-size=64m --security-opt label=disable --env-file "$ENVF" \
    "$img" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
  local r; r=$(wait_health 700)
  if [ "$r" = "0" ]; then log "  ARM $label NOT READY"; docker logs --tail 20 "$C" >> "$OUT" 2>&1; return 1; fi
  log "  ready=${r}s"
  {
    echo "  rocm: $(docker exec "$C" bash -lc 'cat /opt/rocm/.info/version 2>/dev/null || echo 7.14'; )"
    docker exec "$C" bash -lc 'grep -aE "rocBLAS tuning|rocBLAS .*not|plain hipBLAS|HIP device 0" /data/strata-huihui-ud-iq4_xs.log | tail -3'
    docker exec "$C" bash -lc 'grep -a "prefill gemm" /data/strata-huihui-ud-iq4_xs.log | tail -2'
  } >> "$OUT" 2>&1
  ( cd /home/albus/strata166/tmp && python3 mt_read.py 8090 "$label" "$DATA/w850_read_$label.json" 3718,6666,24000 1 kl_pool2.json 0 2 ) >> "$OUT" 2>&1
  ( cd /home/albus/strata166/tmp && python3 mt_gen.py 8090 "$label" "$DATA/w850_gen_$label.json" dec_corpus.json 200 3 ) >> "$OUT" 2>&1
  docker exec "$C" bash -lc 'grep -aE "read in [0-9]+ ms" /data/strata-huihui-ud-iq4_xs.log | tail -8' >> "$OUT" 2>&1
  log "  ARM $label done $(date +%H:%M:%S)"
}

for spec in "strata-gfx906:0.2.9t2 A" "strata-gfx906:0.2.9r1 B" "strata-gfx906:0.2.9t2 A2"; do
  set -- $spec
  arm "$1" "$2" || { restore_prod "strata166-407.arm-$2"; log "ABORT by arm $2"; exit 1; }
done

# 收尾：把 A2 的容器停掉，恢复正式容器（用 pre 的那份容器名）
log "== 收尾：恢复生产容器"
docker stop -t 30 "$C" >/dev/null 2>&1
docker rm -f "$C" >/dev/null 2>&1
# 用 0.2.9t2 起一个新的正式容器（保持原名）
docker run -d --name "$C" --restart unless-stopped --network bridge -p 8090:8090 \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  --device /dev/kfd --device /dev/dri --group-add video \
  --ipc=host --shm-size=64m --security-opt label=disable --env-file "$ENVF" \
  "$PROD" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090" >> "$OUT" 2>&1
r=$(wait_health 700); log "== 生产恢复 ready=${r}s image=$(docker inspect "$C" --format '{{.Config.Image}}')"
bash /home/albus/strata166/tmp/verify_patches.sh >> "$OUT" 2>&1
grep -a "GATE" "$OUT" | tail -1 | sed 's/^/   /'
log "== DONE $OUT"
