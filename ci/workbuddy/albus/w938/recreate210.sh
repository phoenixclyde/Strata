#!/bin/bash
set -u
C=strata166-407
NEWIMG=strata-gfx906:0.2.10-101

echo "=== 1) 优雅停止（让 --expert-profile-save 落盘） ==="
docker stop -t 60 $C >/dev/null 2>&1 && echo "stopped"

echo
echo "=== 2) 旧容器改名保留（回滚用） ==="
docker rename $C ${C}.pre-210 && docker ps -a --format "{{.Names}} {{.Status}}" | grep -E "pre-210|strata166" | head -4

echo
echo "=== 3) 用新镜像起容器（参数逐字复现） ==="
docker run -d --name $C --restart unless-stopped \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  --device /dev/kfd:/dev/kfd --device /dev/dri:/dev/dri \
  -p 8090:8090 --ulimit memlock=-1:-1 --group-add video \
  --security-opt label=disable --ipc host --shm-size 67108864 \
  --workdir /src $NEWIMG \
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090' >/dev/null 2>&1
echo "run rc=$?"
docker ps --format "{{.Names}} {{.Image}} {{.Status}}" | grep $C

echo
echo "=== 4) 等 health ==="
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done
curl -s -m 5 http://127.0.0.1:8090/health | head -c 200; echo

echo
echo "=== 5) 版本三方对齐 ==="
docker exec $C sh -lc 'grep -m1 "project(strata VERSION" /src/CMakeLists.txt; md5sum /src/serve/server.py | cut -c1-32; cat /src/BUILD-IMAGE.json'
docker exec $C sh -lc 'P=$(pgrep -f "strata-0.1.56 --serve" | head -1); echo "engine pid=$P"; md5sum /proc/$P/exe | cut -c1-32; grep VmLck /proc/$P/status'
