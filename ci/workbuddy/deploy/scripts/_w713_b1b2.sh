#!/usr/bin/env bash
# W713 B1b-2 收口：① 答案是否变（贪心同 prompt 对比）② 在 0.1.41 上复核 chunk 三臂 ③ 冷预填代价入结论
#   臂: A = --prefill auto  / every 8192（现役）   B = 4096/4096   C = 2048/2048
#   每臂: restart -> 断言语义 -> 答案探针(3 段长度, 贪心) -> 长度矩阵(25/100/530, 各 2 轮)
#   收尾: **无条件**恢复 params/generated 的生产 config 并重启
set -uo pipefail

W=/home/albus/strata166/w712
LIVE=/home/albus/strata166/data/strata-ud-iq4_xs.json
GEN=/home/albus/strata166/params/generated/strata-ud-iq4_xs.json
ELOG=/home/albus/strata166/data/strata-ud-iq4_xs.log
C=strata166-405
LENS="25 100 530"
LOG=$W/b1b2.log

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

mkcfg() {  # $1=prefill  $2=every  $3=out   （从 params/generated 派生）
  python3 - "$1" "$2" "$3" <<'PYEOF'
import io, json, sys
pf, ev, out = sys.argv[1], sys.argv[2], sys.argv[3]
A = json.load(io.open('/home/albus/strata166/params/generated/strata-ud-iq4_xs.json', encoding='utf-8'))
B = json.loads(json.dumps(A)); a = B['args']
a[a.index('--prefill') + 1] = pf
a[a.index('--prompt-cache-every') + 1] = ev
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(B, indent=1) + '\n')
print('cfg prefill=%s every=%s -> %s' % (pf, ev, out))
PYEOF
}

echo "" >> "$LOG"
say "=== W713 B1b-2 收口开始（引擎 0.1.41 / 容器 $C）==="
say "LIVE md5(before)=$(md5sum $LIVE | cut -d' ' -f1)  GEN md5=$(md5sum $GEN | cut -d' ' -f1)"
for v in "auto 8192 A" "4096 4096 B" "2048 2048 C"; do set -- $v; mkcfg "$1" "$2" "$W/b1b2_cfg_$3.json"; done

run_arm() {
  local tag=$1 cfg=$2
  echo "" >> "$LOG"
  say "########## ARM $tag ##########"
  cp -f "$cfg" "$LIVE"
  docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
  wait_ready || return 1
  say "engine: $(engine_cmdline | grep -oE -- '--(prefill|prompt-cache-every) [a-z0-9]+' | tr '\n' ' ')"
  say "---- $tag 答案探针（贪心，3 段长度）----"
  docker exec "$C" python3 -u /data/bench_answer.py "$tag" 2>&1 | tee -a "$LOG"
  for L in $LENS; do
    local n0; n0=$(wc -l < "$ELOG")
    say "---- $tag 矩阵 len=$L ----"
    docker exec "$C" python3 -u /data/bench_prefix.py "$tag-$L" "$L" 2>&1 | tee -a "$LOG"
    say "--- $tag len=$L 引擎行 ---"
    sed -n "$((n0 + 1)),\$p" "$ELOG" | grep -E 'prompt [0-9]+ tokens' | tail -n 4 | tee -a "$LOG"
  done
  say "---- $tag 答案指纹汇总 ----"
  for i in 0 1 2; do
    f=/home/albus/strata166/data/ans_${tag}_${i}.txt
    [ -f "$f" ] && say "  ans $tag $i len=$(wc -c < "$f") md5=$(md5sum "$f" | cut -d' ' -f1)"
  done
}

run_arm A "$W/b1b2_cfg_A.json"
run_arm B "$W/b1b2_cfg_B.json"
run_arm C "$W/b1b2_cfg_C.json"

echo "" >> "$LOG"
say "########## 收尾：无条件恢复生产 config ##########"
cp -f "$GEN" "$LIVE"
say "LIVE md5=$(md5sum $LIVE | cut -d' ' -f1)  (应为 d2b10f0c4e8293ba010614c7acc70bea)"
docker restart -t 30 "$C" >/dev/null 2>&1; say "restart rc=$?"
wait_ready || say "WARN: 恢复后未就绪"
say "engine: $(engine_cmdline | grep -oE -- '--(prefill|prompt-cache-every) [a-z0-9]+' | tr '\n' ' ')"
say "=== W713 B1b-2 收尾完毕 ==="
