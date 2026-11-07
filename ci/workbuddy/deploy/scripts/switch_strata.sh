#!/usr/bin/env bash
# 通用容器切换（自带轮询 + 自动回滚）。取代一次升级一个的专用脚本。
#   用法: switch_strata.sh <新容器> [旧容器]
#         旧容器省略时 = 当前正在运行的那个 strata 容器（自动探测）
#   行为: 停旧 -> 起新 -> 轮询 /v1/models 至 200（最长 300 s）
#         成功 -> 打印新容器指纹（镜像/启动时刻/引擎 cmdline/LIVE md5/服务面）并退 0
#         失败 -> **自动回滚**（停新、起旧）并退 2/3
set -uo pipefail

NEW=${1:?用法: switch_strata.sh <新容器> [旧容器]}
W=/home/albus/strata166/w712
LOG=$W/switch.log
MODELS=http://127.0.0.1:8090/v1/models
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json

mkdir -p "$W"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

running_strata() {
  docker ps --filter name=strata --format '{{.Names}}' | head -1
}

if [ $# -ge 2 ]; then
  OLD=$2
else
  OLD=$(running_strata)
fi
say "=== switch start: old=${OLD:-<none>} new=$NEW ==="

docker inspect "$NEW" >/dev/null 2>&1 || { say "FATAL: 新容器 $NEW 不存在"; exit 1; }
if [ -n "$OLD" ] && [ "$OLD" = "$NEW" ]; then say "FATAL: 新旧同名"; exit 1; fi

if [ -n "$OLD" ]; then
  docker inspect "$OLD" >/dev/null 2>&1 || { say "FATAL: 旧容器 $OLD 不存在"; exit 1; }
  say "停 $OLD（宽限 30 s）"
  docker stop -t 30 "$OLD" || say "WARN: stop $OLD rc=$?"
fi
say "起 $NEW"
if ! docker start "$NEW"; then
  say "FATAL: $NEW 启动失败；回滚"
  [ -n "$OLD" ] && docker start "$OLD" || true
  exit 2
fi

wait_ready() {
  local i=0 code=""
  while [ "$i" -lt 300 ]; do
    code=$(curl -s -m 6 -o /dev/null -w '%{http_code}' "$MODELS" 2>/dev/null || true)
    if [ "$code" = "200" ]; then say "ready after ${i}s"; return 0; fi
    sleep 5; i=$((i + 5))
  done
  say "NOT ready after 300s（最后 http=$code）"; return 1
}

fingerprint() {
  local c=$1
  say "-- $c 指纹 --"
  docker inspect -f 'image={{.Config.Image}} status={{.State.Status}} started={{.State.StartedAt}}' "$c" | tee -a "$LOG"
  say "engine: $(docker exec "$c" sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) echo "$x";; esac; done' 2>/dev/null | head -1 | grep -oE -- "--(pcie-frac|spec-min-p|prompt-cache-every) [0-9.]+" | tr "\n" " ")"
  say "LIVE md5: $(md5sum "$LIVE" | cut -d' ' -f1)"
}

if wait_ready; then
  say "SUCCESS: $NEW 已在 8090 服务"
  fingerprint "$NEW"
  docker ps -a --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}' | tee -a "$LOG"
  say "=== switch done: OK ==="
  exit 0
fi

say "ROLLBACK: $NEW 未就绪；恢复 $OLD"
docker stop -t 30 "$NEW" || true
[ -n "$OLD" ] && docker start "$OLD" || true
if wait_ready; then
  say "ROLLBACK OK: $OLD 已在服务"
  fingerprint "$OLD"
  say "=== switch done: ROLLED BACK ==="
  exit 3
fi
say "ROLLBACK FAILED: 两个容器都没在服务，需人工处理"
say "=== switch done: MANUAL ==="
exit 4
