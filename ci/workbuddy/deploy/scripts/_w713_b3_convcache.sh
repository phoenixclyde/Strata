#!/usr/bin/env bash
# W713 B3 / P31：--conversation-cache-mib 两臂（会话 parking：多轮追问 TTFT + 答案一致性 + 机制计数）
#   A = 默认（等价于 --conversation-cache-mib 0，parking 关）
#   B = --conversation-cache-mib 1024（slots 用默认 4）
#   探针 = /data/bench_conv.py（双会话 A/B 交替、各 3 轮、每轮把上轮回答接回历史）
#   判据 = ①每轮 TTFT（追问是否塌到亚秒）②两臂同轮答案 md5 是否一致 ③引擎日志里
#          `conversation cache: parked|skipped|restored` 计数（机制）④可选的 --session-min-free-mib 不动
#   收尾 = **无条件**恢复 params/generated 的生产 config 并重启
set -uo pipefail

W=/home/albus/strata166/w712
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
C=strata166-405
LOG=$W/b3.log

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

engine_args() {
  docker exec "$C" sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) echo "$x";; esac; done' 2>/dev/null | head -1 | grep -oE -- '--conversation-cache-mib [0-9]+' || echo '(无 --conversation-cache-mib)'
}

mkcfg() {  # $1=mib 值（空=不设该 flag）  $2=out
  python3 - "$1" "$2" <<'PYEOF'
import io, json, sys
v, out = sys.argv[1], sys.argv[2]
A = json.load(io.open('/home/albus/strata166/params/generated/strata-ud-iq4_xs.json', encoding='utf-8'))
B = json.loads(json.dumps(A)); a = B['args']
if v == '':
    while '--conversation-cache-mib' in a:
        i = a.index('--conversation-cache-mib'); del a[i:i+2]
else:
    if '--conversation-cache-mib' in a:
        a[a.index('--conversation-cache-mib') + 1] = v
    else:
        a += ['--conversation-cache-mib', v]
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(B, indent=1) + '\n')
print('cfg conversation-cache-mib=%r -> %s' % (v or '(unset)', out))
PYEOF
}

echo "" >> "$LOG"
say "=== W713 B3 开始（--conversation-cache-mib 两臂；容器 $C；引擎 0.1.41）==="
say "LIVE md5(before)=$(md5sum $LIVE | cut -d' ' -f1)"
mkcfg ""    "$W/b3_cfg_A.json"
mkcfg 1024  "$W/b3_cfg_B.json"

run_arm() {
  local tag=$1 cfg=$2
  echo "" >> "$LOG"
  say "########## ARM $tag ##########"
  local c0; c0=$(grep -c 'conversation cache:' "$ELOG" 2>/dev/null || echo 0)
  cp -f "$cfg" "$LIVE"
  docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
  wait_ready || return 1
  say "engine: $(engine_args)"
  docker exec "$C" python3 -u /data/bench_conv.py "$tag" 120 2>&1 | tee -a "$LOG"
  local c1; c1=$(grep -c 'conversation cache:' "$ELOG" 2>/dev/null || echo 0)
  say "机制：本臂新增 `conversation cache:` 行数 = $((c1 - c0))"
  sed -n "$(( $(wc -l < "$ELOG") > 200 ? $(wc -l < "$ELOG") - 200 : 1 )),\$p" "$ELOG" | grep 'conversation cache:' | tail -n 6 | tee -a "$LOG"
  for k in A B; do
    for t in 0 1 2; do
      f=/home/albus/strata166/data/conv_${tag}_${k}_${t}.txt
      [ -f "$f" ] && say "  ans $tag $k $t len=$(wc -c < "$f") md5=$(md5sum "$f" | cut -d' ' -f1 | cut -c1-12)"
    done
  done
}

run_arm A "$W/b3_cfg_A.json"
run_arm B "$W/b3_cfg_B.json"

echo "" >> "$LOG"
say "########## 收尾：无条件恢复生产 config ##########"
cp -f "$GEN" "$LIVE"
say "LIVE md5=$(md5sum $LIVE | cut -d' ' -f1)  (应为 d2b10f0c4e8293ba010614c7acc70bea)"
docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
wait_ready || say "WARN: 恢复后未就绪"
say "engine: $(engine_args)"
say "=== W713 B3 收尾完毕 ==="
