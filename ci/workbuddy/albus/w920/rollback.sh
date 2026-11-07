#!/bin/bash
echo "=== 回滚：删新容器，恢复旧容器 ==="
docker stop --timeout 30 strata166-407
docker rm -f strata166-407
docker rename strata166-407.pre-w920 strata166-407
docker start strata166-407
echo "start rc=$?"

echo "=== 等 health ==="
for i in $(seq 1 84); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in
    *'"ok"'*) echo "UP after $((i*5))s"; break;;
  esac
  sleep 5
done

echo
echo "=== 验证：complement 是否恢复 page-locked，ulimit 是否回到 8 MiB ==="
docker exec strata166-407 sh -c 'ulimit -l'
docker exec strata166-407 sh -c "tail -700 /data/strata-huihui-ud-iq4_xs.log | grep -E 'page-locked cache complement|mapped pinned|resident RAM mode|PLE table|expert cache [0-9]+ slots|VRAM free' | cut -c1-165"

echo
echo "=== VmLck（应回到 0）==="
docker exec strata166-407 sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); grep -E "VmLck" /proc/$P/status'

echo
echo "=== 容器参数确认（应无 memlock ulimit）==="
docker inspect -f '{{json .HostConfig.Ulimits}} | {{.HostConfig.NetworkMode}} | {{.Config.Image}}' strata166-407
echo "=== 宿主内存 ==="
free -g | head -2
