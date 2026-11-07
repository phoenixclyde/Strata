#!/usr/bin/env bash
# 升级闸门（每次换引擎后必跑，约 10 分钟） -  判据固定，跨版本可对齐。
#   用法: upgrade_gate.sh [标签]         # 标签默认取当前引擎版本（写进日志便于对齐）
#   第 1 步 服务面（约 1 分钟）：/v1/models + /proc 引擎 cmdline + LIVE md5 + 引擎版本行
#   第 2 步 中性矩阵（约 10 分钟，Z0=off）：bench_prefix 100 / 220 / 530 各 2 轮
#           产出 reused（机制量，确定性）+ 冷/温 TTFT + 冷预填 tok/s，供与**上一版同口径**对比
#   注：register/复验那两项由本机 `verify_config.py` 单独跑（闸门不重复实现）
set -uo pipefail

TAG=${1:-unknown}
W=/home/albus/strata166/w712
LOG=$W/gate.log
MODELS=http://127.0.0.1:8090/v1/models
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
C=$(docker ps --filter name=strata --format '{{.Names}}' | head -1)

say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

echo "" >> "$LOG"
say "########## UPGRADE GATE  版本=$TAG  容器=$C ##########"

# ---------- 第 1 步 服务面 ----------
say "---- 第 1 步：服务面 ----"
code=$(curl -s -m 8 -o /dev/null -w '%{http_code}' "$MODELS" 2>/dev/null || true)
say "1.1 /v1/models http=$code"
say "1.2 models body: $(curl -s -m 8 "$MODELS" | head -c 200)"
say "1.3 engine version: $(docker exec "$C" bash -lc '/src/build-906/strata --version 2>&1 | head -1' 2>/dev/null)"
say "1.4 engine cmdline: $(docker exec "$C" sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) echo "$x";; esac; done' 2>/dev/null | head -1)"
say "1.5 LIVE md5: $(md5sum "$LIVE" | cut -d' ' -f1)   （未改参数时应恒为 d2b10f0c4e8293ba010614c7acc70bea）"
say "1.6 containers: $(docker ps -a --filter name=strata --format '{{.Names}}:{{.Status}}' | tr '\n' ' ')"
say "1.7 长 prompt lend coverage 告警计数: $(grep -c 'lend coverage' "$ELOG" 2>/dev/null || echo 0)"

# ---------- 第 2 步 中性矩阵 ----------
say "---- 第 2 步：中性矩阵（Z0=off；长度 100 / 220 / 530 段）----"
for L in 100 220 530; do
  n0=$(wc -l < "$ELOG")
  say ">>> len=$L"
  docker exec "$C" python3 -u /data/bench_prefix.py "gate-$TAG-$L" "$L" 2>&1 | tee -a "$LOG"
  say "--- len=$L 引擎日志 ---"
  sed -n "$((n0 + 1)),\$p" "$ELOG" | grep -E 'prompt [0-9]+ tokens' | tail -n 4 | tee -a "$LOG"
done

say "=== UPGRADE GATE done ($TAG) ==="
