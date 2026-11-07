#!/bin/bash
# W820: 单臂 = 停生产 -> (可选)清页缓存 -> 起一次性容器 -> 等就绪 -> 3 个读长 -> 抽相位。
# 用法: w820_arm.sh <arm> <config.json> <容器名> [镜像] [ready超时] [measure:0|1] [额外挂载 host:ctr] [drop_caches:0|1]
# 生产容器只 stop 不 rm，随时可 start 回去；日志在 rm 之前落盘（W820 事故教训）。
set -u
ARM="$1"; CFG="$2"; NAME="$3"; IMG="${4:-strata-gfx906:0.2.4p4}"; TO="${5:-900}"; MEAS="${6:-1}"
MOUNT="${7:-}"; DROP="${8:-0}"
DATA=/home/albus/strata166/data
LOG=$DATA/w820_arm_${ARM}.log

echo "=== ARM $ARM  cfg=$(basename "$CFG")  img=$IMG  drop=$DROP  $(date +%H:%M:%S)"
docker stop strata166-407 >/dev/null 2>&1 && echo "  production stopped" || echo "  production not running"
sleep 2
if [ "$DROP" = "1" ]; then
  sudo -n sh -c 'sync; echo 1 > /proc/sys/vm/drop_caches' 2>/dev/null && echo "  drop_caches ok" || echo "  drop_caches FAILED"
fi
echo "  MemAvailable before: $(awk '/MemAvailable/{print int($2/1024)" MiB"}' /proc/meminfo)"

docker rm -f "$NAME" >/dev/null 2>&1
EXTRA=""
[ -n "$MOUNT" ] && EXTRA="-v $MOUNT"
docker run -d --name "$NAME" \
  --ulimit memlock=-1 --ipc host --security-opt label=disable \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  -p 8090:8090 -v /models:/models -v "$DATA":/data $EXTRA \
  -e HSA_OVERRIDE_GFX_VERSION=9.0.6 -e STRATA_SRC=/src \
  "$IMG" bash -lc "cd /src && exec python3 serve/server.py --engine strata --config $CFG --port 8090" >/dev/null
echo "  container up at $(date +%H:%M:%S)"

# 前置检查：容器内配置必须存在、进程必须活着（否则立刻报错，不空等 TO 秒）
sleep 8
docker exec "$NAME" test -f "$CFG" 2>/dev/null || echo "  WARNING: $CFG 在容器内不存在（注意：--config 要用容器路径 /data/...）"
if ! docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true; then
  echo "  !! container died within 8 s — 日志尾部："
  docker logs "$NAME" 2>&1 | tail -14 | cut -c1-160
  echo "=== ARM $ARM ABORTED（容器未存活）"
  exit 3
fi

READY=""
for i in $(seq 1 "$TO"); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then READY=$i; break; fi
  sleep 1
done
echo "  READY=${READY}s"

# 日志先落盘（无论后面做什么）
docker logs "$NAME" > "$LOG" 2>&1
echo "  --- 引擎版本 / 锁定 / rocBLAS ---"
grep -a -E "^strata (generate|serve)|PLE table mlock failed|rocBLAS tuning|--ple-io ram chosen|PLE on, table" "$LOG" | head -6 | cut -c1-170

if [ "$MEAS" = "1" ] && [ -n "$READY" ]; then
  cd /home/albus/strata166/tmp || exit 1
  echo "  --- 读长 1500/3000/6000 ---"
  python3 mt_read.py 8090 "$ARM" "$DATA/w820_${ARM}.json" 1500,3000,6000 1 kl_pool.json 0 > /tmp/w820_${ARM}_read.txt 2>&1 || true
  tail -5 /tmp/w820_${ARM}_read.txt
  echo "  --- 解码 3 条 × 128 token（T=0） ---"
  python3 mt_gen.py 8090 "$ARM" "$DATA/w820_${ARM}_dec.json" dec_corpus.json 128 3 > /tmp/w820_${ARM}_dec.txt 2>&1 || true
  grep -a -iE "decode|tok/s" /tmp/w820_${ARM}_dec.txt | tail -6
  docker logs "$NAME" > "$LOG" 2>&1
fi

echo "  --- 相位 ---"
grep -a "strata prefill timing" "$LOG" | sed -E 's/.*timing: ([0-9]+) tokens, GPU timeline ([0-9]+) ms.* ple ([0-9]+) \(([0-9.]+)%\).*/\1 tok  timeline \2 ms  ple \3 ms (\4%)/' | tail -6
echo "  --- 竞技场/槽位 ---"
grep -a -E "expert arena: |expert cache [0-9]+ slots|MiB of VRAM free" "$LOG" | tail -3 | cut -c1-150
P=$(docker exec "$NAME" pgrep -f "strata --serve" 2>/dev/null | head -1)
if [ -n "${P:-}" ]; then
  echo "  --- 表文件常驻页 ---"
  docker exec "$NAME" bash -lc "awk '/\.gguf/{name=\$6} /^Rss:/{if(name ~ /-0000[23]-of-00003/) s[name]+=\$2} END{for(k in s) printf \"  %9.1f MB %s\n\", s[k]/1024, k}' /proc/$P/smaps | sort -rn | head -4" 2>/dev/null
fi
echo "=== ARM $ARM DONE  log=$LOG"
