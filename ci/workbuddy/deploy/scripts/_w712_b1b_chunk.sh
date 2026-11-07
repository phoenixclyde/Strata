#!/usr/bin/env bash
# W712 B1b: prefill chunk 调小能否让短会话吃上前缀复用（三臂，臂内三档长度）
#   A = --prefill auto  / --prompt-cache-every 8192   (现役)
#   B = --prefill 4096  / --prompt-cache-every 4096   (成对改；机制要求对齐)
#   C = --prefill 2048  / --prompt-cache-every 2048
#   长度: 25(约 1,100 tok) / 100(约 4,600 tok) / 530(约 23,900 tok)
#   判据: reused(机制) + 温 TTFT(体验) + 530 档的预填 tok/s(代价)
#   收尾: **无条件**恢复 params/generated 的生产 config 并重启就绪
set -uo pipefail

W=/home/albus/strata166/w712
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
C=strata166-404
LENS="25 100 530"
LOG=$W/b1b.log

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

mkcfg() {  # $1=prefill_val  $2=every_val  $3=outfile  (一律从 params/generated 派生)
  python3 - "$1" "$2" "$3" <<'PYEOF'
import io, json, sys
pf, ev, out = sys.argv[1], sys.argv[2], sys.argv[3]
A = json.load(io.open('/home/albus/strata166/params/generated/strata-ud-iq4_xs.json', encoding='utf-8'))
B = json.loads(json.dumps(A))
a = B['args']
a[a.index('--prefill') + 1] = pf
a[a.index('--prompt-cache-every') + 1] = ev
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(B, indent=1) + '\n')
print('cfg prefill=%s every=%s -> %s' % (pf, ev, out))
PYEOF
}

echo "=== W712 B1b start: prefill chunk 调小 x 短会话复用 ===" | tee -a "$LOG"
date '+%F %T' | tee -a "$LOG"
say "LIVE md5(before) = $(md5sum $LIVE | cut -d' ' -f1)"
say "GEN  md5        = $(md5sum $GEN | cut -d' ' -f1)"

mkcfg auto 8192  "$W/b1b_cfg_A.json"
mkcfg 4096 4096  "$W/b1b_cfg_B.json"
mkcfg 2048 2048  "$W/b1b_cfg_C.json"
say "-- 各臂与生产 config 的差异（A 应 0 处；B/C 应各 2 处）--"
for t in A B C; do say "diff $t:"; diff "$GEN" "$W/b1b_cfg_$t.json" | tee -a "$LOG"; done

run_arm() {  # $1=tag  $2=cfgfile
  local tag=$1 cfg=$2
  echo "" >> "$LOG"
  say "########## ARM $tag  ($cfg) ##########"
  cp -f "$cfg" "$LIVE"
  say "LIVE md5 = $(md5sum $LIVE | cut -d' ' -f1)"
  docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
  wait_ready || return 1
  say "engine: $(engine_cmdline | grep -o -- '--prefill [a-z0-9:]*') / $(engine_cmdline | grep -o -- '--prompt-cache-every [0-9]*')"
  for L in $LENS; do
    local n0; n0=$(wc -l < "$ELOG")
    say "---- $tag len=$L : bench_prefix $L ----"
    docker exec "$C" python3 -u /data/bench_prefix.py "$tag-$L" "$L" 2>&1 | tee -a "$LOG"
    say "---- $tag len=$L : engine log ----"
    sed -n "$((n0 + 1)),\$p" "$ELOG" | grep -E 'prompt [0-9]+ tokens' | tail -n 4 | tee -a "$LOG"
  done
}

run_arm A "$W/b1b_cfg_A.json"
run_arm B "$W/b1b_cfg_B.json"
run_arm C "$W/b1b_cfg_C.json"

echo "" >> "$LOG"
say "########## 收尾：无条件恢复生产 config ##########"
cp -f "$GEN" "$LIVE"
say "LIVE md5 = $(md5sum $LIVE | cut -d' ' -f1)  (应为 d2b10f0c4e8293ba010614c7acc70bea)"
docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
wait_ready || say "WARN: 恢复后未就绪"
say "engine: $(engine_cmdline | grep -o -- '--prefill [a-z0-9:]*') / $(engine_cmdline | grep -o -- '--prompt-cache-every [0-9]*')"
docker ps -a --filter name=strata --format '{{.Names}} | {{.Status}} | {{.Image}}' | tee -a "$LOG"
say "=== W712 B1b done ==="
