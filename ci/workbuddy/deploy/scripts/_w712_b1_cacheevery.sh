#!/usr/bin/env bash
# W712 B1: --prompt-cache-every 的 <8k / 8-16k / >16k 三档边界（单变量 A/B/C，臂内多长度）
#   臂: 8192(现役 A) / 16384(旧默认 B) / 32768(候选 C)
#   长度: 100(~4.5k, <8k) / 220(~9.9k, 8-16k 正对照) / 530(~23.9k, >16k)
#   判据: 机制量 reused（确定性）+ 温 TTFT；每臂末断言容器里跑的就是该臂的 config
#   收尾: **无条件**恢复 params/generated 的生产 config（8192）并重启就绪
set -uo pipefail

W=/home/albus/strata166/w712
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
C=strata166-404
LENS="100 220 530"
LOG=$W/b1.log

mkdir -p "$W"
say() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

wait_ready() {
  local i=0 code
  while [ "$i" -lt 420 ]; do
    code=$(curl -s -m 6 -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/v1/models 2>/dev/null || true)
    if [ "$code" = "200" ]; then say "ready after ${i}s"; return 0; fi
    sleep 10; i=$((i + 10))
  done
  say "NOT READY after 420s"; return 1
}

engine_cmdline() {
  docker exec "$C" sh -c 'for p in /proc/[0-9]*/cmdline; do x=$(tr "\0" " " < "$p"); case "$x" in *build-906/strata*) echo "$x";; esac; done' 2>/dev/null | head -1
}

mkcfg() {  # $1=value  $2=outfile   -  一律从 params/generated 派生（稳定基准）
  python3 - "$1" "$2" <<'PYEOF'
import io, json, sys
val, out = sys.argv[1], sys.argv[2]
A = json.load(io.open('/home/albus/strata166/params/generated/strata-ud-iq4_xs.json', encoding='utf-8'))
B = json.loads(json.dumps(A))
k = '--prompt-cache-every'
a = B['args']
assert k in a, 'anchor flag missing'
a[a.index(k) + 1] = val
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(B, indent=1) + '\n')
print('cfg %s -> %s' % (val, out))
PYEOF
}

echo "=== W712 B1 start: --prompt-cache-every 三档边界 ===" | tee -a "$LOG"
date '+%F %T' | tee -a "$LOG"
say "LIVE md5(before) = $(md5sum $LIVE | cut -d' ' -f1)"
say "GEN  md5        = $(md5sum $GEN | cut -d' ' -f1)"

for v in 8192 16384 32768; do mkcfg "$v" "$W/cfg_$v.json"; done
say "-- 三份 cfg 与生产 config 的差异（应各恰一处）--"
for v in 8192 16384 32768; do
  say "diff $v:"; diff "$GEN" "$W/cfg_$v.json" | tee -a "$LOG"
done

run_arm() {  # $1=tag  $2=cfgfile
  local tag=$1 cfg=$2
  echo "" >> "$LOG"
  say "########## ARM $tag  ($cfg) ##########"
  cp -f "$cfg" "$LIVE"
  say "LIVE md5 = $(md5sum $LIVE | cut -d' ' -f1)"
  docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
  wait_ready || return 1
  say "engine: $(engine_cmdline | grep -o -- '--prompt-cache-every [0-9]*')"
  for L in $LENS; do
    local n0; n0=$(wc -l < "$ELOG")
    say "---- $tag len=$L : bench_prefix $L ----"
    docker exec "$C" python3 -u /data/bench_prefix.py "$tag-$L" "$L" 2>&1 | tee -a "$LOG"
    say "---- $tag len=$L : engine log ----"
    sed -n "$((n0 + 1)),\$p" "$ELOG" | grep -E 'prompt [0-9]+ tokens' | tail -n 4 | tee -a "$LOG"
  done
}

run_arm A8192  "$W/cfg_8192.json"
run_arm B16384 "$W/cfg_16384.json"
run_arm C32768 "$W/cfg_32768.json"

echo "" >> "$LOG"
say "########## 收尾：无条件恢复生产 config ##########"
cp -f "$GEN" "$LIVE"
say "LIVE md5 = $(md5sum $LIVE | cut -d' ' -f1)  (应为 d2b10f0c4e8293ba010614c7acc70bea)"
docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
wait_ready || say "WARN: 恢复后未就绪"
say "engine: $(engine_cmdline | grep -o -- '--prompt-cache-every [0-9]*')"
docker ps -a --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}' | tee -a "$LOG"
say "=== W712 B1 done ==="
