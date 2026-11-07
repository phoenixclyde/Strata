#!/usr/bin/env bash
# W712: Strata gfx906 0.1.40.2 -> 0.1.40.4 切换（带自动回滚）
#   停 strata166-402 -> 起 strata166-404 -> 轮询 /v1/models 至 200（最长 300 s）
#   成功: 记录新引擎指纹并退出 0
#   失败: 自动回滚（停 -404、起 -402）并退出 2
# 用法（166 上）: /home/albus/strata166/w712/switch_404.sh
set -uo pipefail

OLD=strata166-402
NEW=strata166-404
DIR=/home/albus/strata166/w712
LOG=$DIR/switch_404.log
MODELS=http://127.0.0.1:8090/v1/models
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json

mkdir -p "$DIR"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

wait_ready() {  # $1 container  $2 timeout seconds
  local c=$1 t=$2 i=0 code=""
  while [ "$i" -lt "$t" ]; do
    code=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "$MODELS" 2>/dev/null || true)
    if [ "$code" = "200" ]; then say "$c ready after ${i}s"; return 0; fi
    sleep 5; i=$((i + 5))
  done
  say "$c NOT ready after ${t}s (last http=$code)"
  return 1
}

fingerprint() {  # $1 container
  local c=$1
  say "-- $c fingerprint --"
  docker inspect -f 'image={{.Config.Image}} status={{.State.Status}} started={{.State.StartedAt}}' "$c" | tee -a "$LOG"
  docker exec "$c" sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) echo "ENGINE: $x";; esac; done' 2>&1 | tee -a "$LOG"
  say "LIVE md5: $(md5sum "$LIVE" | cut -d' ' -f1)"
  say "models: $(curl -s -m 5 "$MODELS" | head -c 220)"
}

say "=== W712 switch start (old=$OLD new=$NEW) ==="
docker inspect "$NEW" >/dev/null 2>&1 || { say "FATAL: container $NEW does not exist"; exit 1; }
docker inspect "$OLD" >/dev/null 2>&1 || { say "FATAL: container $OLD does not exist"; exit 1; }

say "stopping $OLD (grace 30s)"
docker stop -t 30 "$OLD" || say "WARN: stop $OLD rc=$? (continuing)"
say "starting $NEW"
if ! docker start "$NEW"; then
  say "FATAL: start $NEW failed; restoring $OLD"
  docker start "$OLD" || true
  exit 2
fi

if wait_ready "$NEW" 300; then
  say "SUCCESS: $NEW serving on 8090"
  fingerprint "$NEW"
  docker ps -a --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}' | tee -a "$LOG"
  say "=== W712 switch done: OK ==="
  exit 0
fi

say "ROLLBACK: $NEW not ready; restoring $OLD"
docker stop -t 30 "$NEW" || true
docker start "$OLD" || true
if wait_ready "$OLD" 300; then
  say "ROLLBACK OK: $OLD serving; production back on 0.1.40.2"
  fingerprint "$OLD"
  say "=== W712 switch done: ROLLED BACK ==="
  exit 2
fi
say "ROLLBACK FAILED: neither container serves; manual action needed"
say "=== W712 switch done: MANUAL ==="
exit 3
