#!/bin/bash
# W824: 单臂 = 停生产 -> 起一次性容器 -> 等就绪 -> 读长/解码 -> 抽相位。
# 用法: w824_arm.sh <arm> <容器内配置路径> <容器名> [镜像] [ready超时] [measure:0|1] [额外挂载 host:ctr]
# 生产容器只 stop 不 rm；日志在 rm 之前落盘。
set -u
ARM="$1"; CFG="$2"; NAME="$3"; IMG="${4:-strata-gfx906:0.2.4p4}"; TO="${5:-900}"; MEAS="${6:-1}"
MOUNT="${7:-}"
DATA=/home/albus/strata166/data
LOG=$DATA/w824_arm_${ARM}.log
PROD=strata166-407

echo "=== ARM $ARM  cfg=$CFG  img=$IMG  $(date +%H:%M:%S)"
# 停生产：限时，避免引擎不理 SIGTERM 时挂住
timeout 90 docker stop -t 20 "$PROD" >/dev/null 2>&1 && echo "  production stopped" || echo "  production stop timeout/absent"
sleep 2
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

# 前置检查：配置存在、进程活着（否则立刻报错，不空等 TO 秒）
sleep 8
docker exec "$NAME" test -f "$CFG" 2>/dev/null || echo "  WARNING: $CFG 在容器内不存在（--config 要用容器路径 /data/...）"
if ! docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true; then
  echo "  !! container died within 8 s — 日志尾部："
  docker logs "$NAME" 2>&1 | tail -16 | cut -c1-160
  echo "=== ARM $ARM ABORTED（容器未存活）"
  exit 3
fi

READY=""
for i in $(seq 1 "$TO"); do
  if curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1; then READY=$i; break; fi
  sleep 1
done
echo "  READY=${READY}s"

docker logs "$NAME" > "$LOG" 2>&1
echo "  --- 版本 / 开关 ---"
grep -a -E "engine started:|PLE table mlock failed|rocBLAS tuning|PLE on, table|native pack:" "$LOG" | head -6 | cut -c1-165
echo "  --- 版本号 ---"
docker exec "$NAME" /src/build-906/strata --version 2>/dev/null || true
if [ -x /home/albus/strata166/src0271_out/strata-0.1.53 ]; then :; fi

if [ "$MEAS" = "1" ] && [ -n "$READY" ]; then
  cd /home/albus/strata166/tmp || exit 1
  echo "  --- 解码 5 条 x 128 token（T=0，放在大 prefill 之前）---"
  python3 mt_gen.py 8090 "$ARM" "$DATA/w824_${ARM}_dec.json" dec_corpus.json 128 5 > /tmp/w824_${ARM}_dec.txt 2>&1 || true
  grep -a -iE "ptok=|tok/s" /tmp/w824_${ARM}_dec.txt | tail -8
  echo "  --- 读长 1500/3000/6000 ---"
  python3 mt_read.py 8090 "$ARM" "$DATA/w824_${ARM}.json" 1500,3000,6000 1 kl_pool.json 0 > /tmp/w824_${ARM}_read.txt 2>&1 || true
  tail -5 /tmp/w824_${ARM}_read.txt
  grep -a -iE "ptok=|tok/s" /tmp/w824_${ARM}_dec.txt | tail -6
  docker logs "$NAME" > "$LOG" 2>&1
fi

echo "  --- 相位 ---"
grep -a "strata prefill timing" "$LOG" | sed -E 's/.*timing: ([0-9]+) tokens, GPU timeline ([0-9]+) ms.* ple ([0-9]+) \(([0-9.]+)%\).*/\1 tok  timeline \2 ms  ple \3 ms (\4%)/' | tail -6
echo "  --- 竞技场/槽位/命中 ---"
grep -a -E "expert arena: |expert cache [0-9]+ slots|MiB of VRAM free|expert cache hit rate|route tail skip" "$LOG" | tail -5 | cut -c1-155
echo "=== ARM $ARM end $(date +%H:%M:%S)"
