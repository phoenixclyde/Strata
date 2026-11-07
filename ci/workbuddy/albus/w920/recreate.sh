#!/bin/bash
set -o pipefail
IMG=strata-gfx906:0.2.9-101

echo "=== 0. 前置核对 ==="
docker inspect -f 'name={{.Name}} image={{.Config.Image}} id={{.Image}}' strata166-407
free -g | head -2

echo "=== 1. 优雅停止（让 expert-profile-save 落盘）==="
docker stop --time 30 strata166-407
echo "stop rc=$?"

echo "=== 2. 改名保留（不删，可回滚）==="
docker rename strata166-407 strata166-407.pre-w920
docker ps -a --format '{{.Names}} {{.Status}}' | grep -E "strata166-407" | head -3

echo "=== 3. 起新容器（加 --ulimit memlock=-1，其余逐字段复现）==="
docker run -d --name strata166-407 \
  --restart unless-stopped \
  --network bridge \
  -p 8090:8090 \
  --ipc host \
  --device /dev/kfd --device /dev/dri \
  --group-add video \
  --security-opt label=disable \
  --shm-size 64m \
  --ulimit memlock=-1 \
  -v /models:/models:ro \
  -v /home/albus/strata166/data:/data \
  "$IMG" \
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090'
echo "run rc=$?"

echo "=== 4. 参数比对（新容器 vs 备份）==="
sleep 3
docker inspect -f '{{json .HostConfig.Ulimits}} | {{.HostConfig.NetworkMode}} | {{.HostConfig.IpcMode}} | {{.HostConfig.ShmSize}} | {{.HostConfig.GroupAdd}} | {{.HostConfig.SecurityOpt}} | {{json .HostConfig.Devices}} | {{json .HostConfig.Binds}} | {{.HostConfig.RestartPolicy.Name}}' strata166-407
docker inspect -f '{{json .Config.Env}}' strata166-407
docker inspect -f '{{json .Config.Cmd}}' strata166-407
