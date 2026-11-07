#!/bin/bash
# W824 KL 轮：逐臂起引擎 -> 用 mt_kl 跑脚本化对话（写 LOGPOS）-> 下一臂；最后恢复生产。
# 用法: w824_kl.sh <arm> [arm...]
set -u
T=/home/albus/strata166/tmp
D=/home/albus/strata166/data
C=w824arm
IMG=strata-gfx906:0.2.4p4
NAME=w824kl
LOG=$D/w824_kl.log
PROD=strata166-407

restore() {
  echo "=== restore $(date +%F' '%T)"
  docker rm -f "$NAME" >/dev/null 2>&1
  docker start "$PROD" >/dev/null 2>&1
  for i in $(seq 1 420); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  production HEALTHY after ${i}s"; return; }
    sleep 1
  done
  echo "  !! production NOT healthy after 420s"
}
trap restore EXIT INT TERM

# 互斥用 flock：pgrep -f 会匹配到发起它的那条命令行（本轮实测误判过）
exec 9>/tmp/w824_kl.lock
flock -n 9 || { echo "REFUSING: another w824_kl.sh holds /tmp/w824_kl.lock"; exit 4; }

: > "$LOG"
{
  echo "### W824 KL start $(date +%F' '%T) arms: $*"
  for a in "$@"; do
    echo "=== KL ARM $a"
    bash $T/w824_arm.sh "$a" "/data/$C/$a.json" "$NAME" "$IMG" 900 0 ""
    cd $T || exit 1
    python3 mt_kl.py kl_corpus.json 8090 "$a" "$D/w824_kl_$a.json" 2>&1 | tail -12
    ls -la "$D/w824kl/w803_logpos_$a.tsv" 2>/dev/null || echo "  !! no logpos file for $a"
    wc -l < "$D/w824kl/w803_logpos_$a.tsv" 2>/dev/null | sed 's/^/  rows: /'
  done
  echo "### W824 KL end $(date +%F' '%T)"
} >> "$LOG" 2>&1
