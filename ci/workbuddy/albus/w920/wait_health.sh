#!/bin/bash
C=strata166-407
LOG=/data/strata-huihui-ud-iq4_xs.log

echo "=== 等 health（最长 420 s）==="
for i in $(seq 1 84); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in
    *'"ok"'*) echo "UP after $((i*5))s"; break;;
  esac
  sleep 5
done

echo
echo "=== 启动期内存/显存关键行（本次 run）==="
docker exec $C sh -c "tail -600 $LOG | grep -E 'RAM budget|page-locked cache complement|mapped pinned|resident RAM mode|expert cache auto|VRAM free|PLE table|mlock' | cut -c1-160"

echo
echo "=== VmLck（PLE 是否真锁住）==="
docker exec $C sh -c 'P=$(pgrep -f "strata-0.1.55t --serve"|head -1); echo "pid=$P"; grep -E "VmLck|VmRSS" /proc/$P/status'

echo
echo "=== ulimit -l 与 limits ==="
docker exec $C sh -c 'ulimit -l; P=$(pgrep -f "strata-0.1.55t --serve"|head -1); grep -i "max locked" /proc/$P/limits'

echo
echo "=== 宿主内存（锁住后）==="
free -g | head -2
