#!/usr/bin/env bash
# W713 B7 / 候选 P35：STRATA_STAGER_SSD 三臂（量化 #1353 对我们的价值）
#   A = 默认（自动：我们实测 100% 页缓存 -> RAM 档 4 线程/16 深/批 1）
#   B = STRATA_STAGER_SSD=1（强制 SSD 档 32 线程/128 深/批 8） -  故意切错档
#   C = STRATA_STAGER_SSD=0（显式强制 RAM 档，应与 A 等同 => 机制对照）
#   判据: 机制 = 引擎日志 "takes the RAM profile" 出现/消失 + 引擎进程 environ 实读；
#         吞吐 = 冷预填 tok/s（预填分辨力 1.2-1.7%），档位 220 / 530
#   收尾: **无条件**恢复 params/generated 的生产 config 并重启
set -uo pipefail

W=/home/albus/strata166/w712
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
C=strata166-405
LENS="220 530"
LOG=$W/b7.log

say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

wait_ready() {
  local i=0 code
  while [ "$i" -lt 420 ]; do
    code=$(curl -s -m 6 -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/v1/models 2>/dev/null || true)
    if [ "$code" = "200" ]; then say "ready after ${i}s"; return 0; fi
    sleep 10; i=$((i + 10))
  done
  say "NOT READY"; return 1
}

engine_env() {  # 直接读引擎进程的 environ（比 config 更硬）
  docker exec "$C" sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) d=$(dirname "$p"); tr "\0" "\n" < "$d/environ" | grep -E "^STRATA_STAGER" || echo "(no STRATA_STAGER_* in engine env)";; esac; done' 2>/dev/null | head -6
}

mkcfg_env() {  # $1=env 值（空=不设）  $2=outfile    -  从 params/generated 派生
  python3 - "$1" "$2" <<'PYEOF'
import io, json, sys
v, out = sys.argv[1], sys.argv[2]
A = json.load(io.open('/home/albus/strata166/params/generated/strata-ud-iq4_xs.json', encoding='utf-8'))
B = json.loads(json.dumps(A))
e = B.setdefault('env', {})
if v == '':
    e.pop('STRATA_STAGER_SSD', None)
else:
    e['STRATA_STAGER_SSD'] = v
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(B, indent=1) + '\n')
print('cfg env.STRATA_STAGER_SSD=%r -> %s' % (v or '(unset)', out))
PYEOF
}

echo "" >> "$LOG"
say "=== W713 B7 开始（STRATA_STAGER_SSD 三臂；容器 $C；引擎 0.1.41）==="
say "LIVE md5(before)=$(md5sum $LIVE | cut -d' ' -f1)"
mkcfg_env ""  "$W/b7_cfg_A.json"
mkcfg_env "1" "$W/b7_cfg_B.json"
mkcfg_env "0" "$W/b7_cfg_C.json"

run_arm() {
  local tag=$1 cfg=$2
  echo "" >> "$LOG"
  say "########## ARM $tag ##########"
  local c0; c0=$(grep -c 'takes the RAM profile' "$ELOG" 2>/dev/null || echo 0)
  cp -f "$cfg" "$LIVE"
  docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
  wait_ready || return 1
  say "engine env: $(engine_env | tr '\n' ' ')"
  local n0; n0=$(wc -l < "$ELOG")
  for L in $LENS; do
    say "---- $tag len=$L ----"
    docker exec "$C" python3 -u /data/bench_prefix.py "$tag-$L" "$L" 2>&1 | tee -a "$LOG"
    say "--- $tag len=$L 引擎行 ---"
    sed -n "$((n0 + 1)),\$p" "$ELOG" | grep -E 'prompt [0-9]+ tokens' | tail -n 4 | tee -a "$LOG"
    n0=$(wc -l < "$ELOG")
  done
  local c1; c1=$(grep -c 'takes the RAM profile' "$ELOG" 2>/dev/null || echo 0)
  say "机制标记：本臂新增 'takes the RAM profile' 行数 = $((c1 - c0))（RAM 档应 =1，强制 SSD 档应 =0）"
}

run_arm A "$W/b7_cfg_A.json"
run_arm B "$W/b7_cfg_B.json"
run_arm C "$W/b7_cfg_C.json"

echo "" >> "$LOG"
say "########## 收尾：无条件恢复生产 config ##########"
cp -f "$GEN" "$LIVE"
say "LIVE md5=$(md5sum $LIVE | cut -d' ' -f1)  (应为 d2b10f0c4e8293ba010614c7acc70bea)"
docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
wait_ready || say "WARN: 恢复后未就绪"
say "engine env: $(engine_env | tr '\n' ' ')"
say "--- 全臂机制标记汇总（每臂引擎启动后是否出现 RAM profile 行）---"
grep -c 'takes the RAM profile' "$ELOG" | tee -a "$LOG"
say "=== W713 B7 收尾完毕 ==="
