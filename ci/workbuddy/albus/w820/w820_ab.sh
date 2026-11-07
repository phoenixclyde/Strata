#!/bin/bash
# W820: A/B 驱动 —— 三臂交错（A=生产 0.1.49.2 / B=0.1.52 / A2=生产），跑完自动恢复生产。
# 用法: w820_ab.sh      （建议 setsid nohup 后台跑；日志 /data/w820_ab.log）
# 设计要点：
#   * 三臂共用同一套配置（A/A2 逐字相同，只有 log 不同），B 只差 exe + 关掉 0.2.7 的自动 PLE 常驻，
#     因此 A↔B 的差异只归因于"引擎版本"；
#   * 不清页缓存（避免 3 分钟满盘 I/O），三臂都在暖缓存下跑，A2 作为漂移检查；
#   * trap 保证任何退出路径都会把生产起回来。
set -u
T=/home/albus/strata166/tmp
D=/home/albus/strata166/data
C=w820arm
IMG=strata-gfx906:0.2.4p4
LOG=$D/w820_ab.log

restore() {
  echo "=== restore $(date +%F' '%T)"
  docker rm -f strata166-w820arm >/dev/null 2>&1
  docker start strata166-407 >/dev/null 2>&1
  for i in $(seq 1 420); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "  production HEALTHY after ${i}s"; return; }
    sleep 1
  done
  echo "  production NOT healthy after 420s"
}
trap restore EXIT INT TERM

: > "$LOG"
{
  echo "### W820 A/B start $(date +%F' '%T)"

  echo "=== ARM A  (0.1.49.2, production binary)"
  bash $T/w820_arm.sh A /data/$C/A.json "$C" "$IMG" 900 1 ""

  echo "=== ARM B  (0.1.52, /opt/newbin)"
  bash $T/w820_arm.sh B /data/$C/B.json "$C" "$IMG" 900 1 "/home/albus/strata166/src027_out:/opt/newbin"

  echo "=== ARM A2 (0.1.49.2 again, drift check)"
  bash $T/w820_arm.sh A2 /data/$C/A2.json "$C" "$IMG" 900 1 ""

  echo "### W820 A/B end $(date +%F' '%T)"
} >> "$LOG" 2>&1
