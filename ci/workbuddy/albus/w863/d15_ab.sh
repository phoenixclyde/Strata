#!/bin/bash
# W863 · R 表 A/B（同镜像同二进制，只差 env STRATA_MMVQ_WAVE_ROWS）
#   T = 默认（实测表）      B = 1（旧行为 R=1）
# 交错 T B T B；每臂 restart -> health -> 丢前 2 请求 -> 3 次固定贪心长生成。
# 安全性：任何异常/中断都会把 env 恢复成生产态（无 STRATA_MMVQ_WAVE_ROWS）再重启。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/w863/ab_$TS.txt
BAK=$CFG.bak_w863ab_$TS
CONT=strata166-407
OKFLAG=/tmp/w863_ab_done
rm -f "$OKFLAG"

set_arm() {   # $1 = T|B
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, arm = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
e = {k: v for k, v in d.get('env', {}).items() if k != 'STRATA_MMVQ_WAVE_ROWS'}
if arm == 'B':
    e['STRATA_MMVQ_WAVE_ROWS'] = '1'
d['env'] = e
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('arm', arm, 'exe', d.get('exe'), 'wave_rows_env', e.get('STRATA_MMVQ_WAVE_ROWS', '(unset)'))
PY
}

restart_up() {
  docker restart "$CONT" >/dev/null 2>&1
  for i in $(seq 1 420); do
    curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
    sleep 1
  done
  sleep 8
}

warm2() {
  python3 - >> "$OUT" 2>&1 <<'PY'
import json, urllib.request
for i in range(2):
    body = {"model": "qwen3.8-flash-next-ud-q4_k_xl-abliterated",
            "messages": [{"role": "user", "content": "回复一个字：好"}],
            "max_tokens": 4, "temperature": 0}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            r.read()
        print("warm %d ok" % i)
    except Exception as ex:
        print("warm %d FAIL %r" % (i, ex))
PY
}

measure() {   # $1 = 次数, $2 = max_tokens
  python3 - "$1" "$2" >> "$OUT" 2>&1 <<'PY'
import json, sys, time, urllib.request
n, mt = int(sys.argv[1]), int(sys.argv[2])
PROMPT = ("下面是一段用于压测解码速度的固定文字，请逐字续写，不要总结、不要换题。"
          "在远程测试台上，我们把显存的每一兆字节都算过一遍：权重按层切分、按需常驻，"
          "专家走缓存，提示走分块，剩下的空间留给 KV。")
for i in range(n):
    body = {"model": "qwen3.8-flash-next-ud-q4_k_xl-abliterated",
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": mt, "temperature": 0}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.loads(r.read())
        u = d.get("usage", {})
        dt = time.time() - t0
        print("run %d: wall=%.3fs completion_tokens=%s" % (i, dt, u.get("completion_tokens")))
    except Exception as ex:
        print("run %d FAIL %r" % (i, ex))
PY
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restore prod env $(date +%H:%M:%S) ===" >> "$OUT"
    python3 - "$CFG" >> "$OUT" 2>&1 <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d['env'] = {k: v for k, v in d.get('env', {}).items() if k != 'STRATA_MMVQ_WAVE_ROWS'}
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print('prod env restored:', sorted(d['env'].items()))
PY
    docker restart "$CONT" >/dev/null 2>&1
    for i in $(seq 1 420); do
      curl -s --max-time 2 http://127.0.0.1:8090/health >/dev/null 2>&1 && { echo "health ${i}s" >> "$OUT"; break; }
      sleep 1
    done
    echo "=== END $(date +%H:%M:%S) ===" >> "$OUT"
  fi
}

cp -f "$CFG" "$BAK"
echo "START $(date +%Y-%m-%d_%H:%M:%S) ts=$TS" > "$OUT"
echo "bak=$BAK" >> "$OUT"
echo "exe=$(python3 -c "import json;print(json.load(open('$CFG'))['exe'])")" >> "$OUT"
echo "bin_md5=$(md5sum /home/albus/strata166/data/bin/strata-0.1.55h | cut -d' ' -f1)" >> "$OUT"
trap 'keepup' EXIT HUP INT TERM

for arm in T B T B; do
  echo "=== ARM $arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_arm "$arm"
  restart_up
  grep -a "engine started" "$LOG" | tail -1 | cut -c1-90 >> "$OUT"
  warm2
  prev=$(wc -l < "$LOG")
  measure 3 480
  tail -n +$((prev + 1)) "$LOG" | grep -a -E "^strata serve: prompt .* generated|^strata decode GPU stages" >> "$OUT"
done

echo "=== RESTORE PROD $(date +%H:%M:%S) ===" >> "$OUT"
set_arm T
restart_up
curl -s --max-time 8 http://127.0.0.1:8090/health >> "$OUT" 2>&1; echo >> "$OUT"
echo "env_final=$(python3 -c "import json;print(sorted(json.load(open('$CFG')).get('env',{}).items()))")" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
