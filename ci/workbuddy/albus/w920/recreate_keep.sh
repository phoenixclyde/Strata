#!/bin/bash
IMG=strata-gfx906:0.2.9-101
echo "=== 1. 停并改名保留 ==="
docker stop --timeout 30 strata166-407 >/dev/null
docker rename strata166-407 strata166-407.pre-w920b
echo "renamed -> $(docker ps -a --format '{{.Names}} {{.Status}}' | grep pre-w920b)"

echo "=== 2. 起新容器（--ulimit memlock=-1）==="
docker run -d --name strata166-407 \
  --restart unless-stopped --network bridge -p 8090:8090 --ipc host \
  --device /dev/kfd --device /dev/dri --group-add video \
  --security-opt label=disable --shm-size 64m \
  --ulimit memlock=-1 \
  -v /models:/models:ro -v /home/albus/strata166/data:/data \
  "$IMG" \
  bash -lc 'cd /src && exec python3 serve/server.py --engine strata --config /data/strata-huihui-ud-iq4_xs.json --port 8090'
echo "run rc=$?"

echo "=== 3. 参数校验 ==="
sleep 3
docker inspect -f 'ulimits={{json .HostConfig.Ulimits}} net={{.HostConfig.NetworkMode}} ipc={{.HostConfig.IpcMode}} shm={{.HostConfig.ShmSize}} grp={{.HostConfig.GroupAdd}} sec={{.HostConfig.SecurityOpt}} rp={{.HostConfig.RestartPolicy.Name}} img={{.Config.Image}}' strata166-407

echo "=== 4. 等 health ==="
for i in $(seq 1 84); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 5. 验证 VmLck 与 PLE ==="
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo "pid=$P"; grep VmLck /proc/$P/status; ulimit -l'
docker exec strata166-407 sh -c "grep -E 'PLE table' /data/strata-huihui-ud-iq4_xs.log | tail -2 | cut -c1-120"
free -g | head -2
