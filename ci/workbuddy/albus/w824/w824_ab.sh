#!/bin/bash
# W824: 驱动 —— 交错多臂，跑完自动恢复生产。
# 用法: w824_ab.sh A B53 A2 [T1 T2 ...]
#   配置在 /home/albus/strata166/data/w824arm/<ARM>.json
#   只有 B53 需要额外挂载 0.1.53 所在目录；其余用生产二进制。
set -u
T=/home/albus/strata166/tmp
D=/home/albus/strata166/data
C=w824arm
IMG=strata-gfx906:0.2.4p4
NAME=w824arm                       # 容器名：restore 必须用同一个变量（W820 的 19 小时残留就是名字写错）
LOG=$D/w824_ab.log
PROD=strata166-407

restore() {
  echo "=== restore $(date +%F' '%T)"
  docker rm -f "$NAME" >/dev/null 2>&1
  # 顺手清掉历史遗留的实验容器名
  for n in w820arm w822t w822m strata166-w820a; do docker rm -f "$n" >/dev/null 2>&1; done
  docker start "$PROD" >/dev/null 2>&1
  for i in $(seq 1 420); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  production HEALTHY after ${i}s"; return; }
    sleep 1
  done
  echo "  !! production NOT healthy after 420s"
}
trap restore EXIT INT TERM

ARMS="$*"
[ -z "$ARMS" ] && { echo "usage: w824_ab.sh <arm> [arm...]"; exit 2; }

# 护栏：同一时刻只许一个驱动（W824 教训：两个驱动抢同一个容器名，后起的会 rm -f 掉前一个的容器）
OTHER=$(pgrep -f "w824_ab.sh" | grep -v "^$$" | head -1)
if [ -n "${OTHER:-}" ]; then
  echo "REFUSING: another w824_ab.sh is running (pid $OTHER); kill it first (kill -9 to skip its trap)"
  exit 4
fi

: > "$LOG"
{
  echo "### W824 driver start $(date +%F' '%T)  arms: $ARMS"
  for a in $ARMS; do
    MT=""
    case "$a" in
      B53*) MT="/home/albus/strata166/src0271_out:/opt/newbin" ;;
    esac
    echo "=== ARM $a  mount=${MT:-none}"
    bash $T/w824_arm.sh "$a" "/data/$C/$a.json" "$NAME" "$IMG" 900 1 "$MT"
  done
  echo "### W824 driver end $(date +%F' '%T)"
} >> "$LOG" 2>&1
