#!/usr/bin/env bash
# W713 B3c：单会话重复性 + parking 一致性（决定性分辨）
#   A = 默认（cache off，等价 mib=0）；B = --conversation-cache-mib 1024
#   每臂跑 bench_conv1.py（单会话、3 轮、重复 2 次）
#   收尾无条件恢复生产 config
set -uo pipefail

W=/home/albus/strata166/w712
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
C=strata166-405
LOG=$W/b3c.log

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
mkcfg() {  # $1=mib 值（空=移除该 flag）
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
PYEOF
}

echo "" >> "$LOG"
say "=== W713 B3c 开始（单会话重复性 + parking 一致性；容器 $C）==="
mkcfg ""   "$W/b3c_cfg_A.json"
mkcfg 1024 "$W/b3c_cfg_B.json"

run_arm() {
  local tag=$1 cfg=$2
  say "########## ARM $tag ##########"
  local c0; c0=$(grep -c 'conversation cache:' "$ELOG" 2>/dev/null || echo 0)
  cp -f "$cfg" "$LIVE"
  docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
  wait_ready || return 1
  docker exec "$C" python3 -u /data/bench_conv1.py "$tag" 2 2>&1 | tee -a "$LOG"
  local c1; c1=$(grep -c 'conversation cache:' "$ELOG" 2>/dev/null || echo 0)
  say "机制：本臂新增 conversation cache 行数 = $((c1 - c0))"
}

run_arm A "$W/b3c_cfg_A.json"
run_arm B "$W/b3c_cfg_B.json"

say "---- 文件指纹（本机侧比对用）----"
for t in A B; do for r in 1 2; do for n in 0 1 2; do
  f=/home/albus/strata166/data/c1_${t}_r${r}_t${n}.txt
  [ -f "$f" ] && say "  c1 $t r$r t$n len=$(wc -c < "$f") md5=$(md5sum "$f" | cut -d' ' -f1 | cut -c1-12)"
done; done; done

echo "" >> "$LOG"
say "########## 收尾：无条件恢复生产 config ##########"
cp -f "$GEN" "$LIVE"
say "LIVE md5=$(md5sum $LIVE | cut -d' ' -f1)  (应为 d2b10f0c4e8293ba010614c7acc70bea)"
docker restart -t 30 "$C" >/dev/null 2>&1
wait_ready || say "WARN: 恢复后未就绪"
say "=== W713 B3c 收尾完毕 ==="
