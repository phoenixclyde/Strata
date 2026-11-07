#!/bin/bash
# W863 · A/B：--spec-min-p 0.70（现状） vs 0.40（让草稿链更长）
# 唯一变量；A B A B 交错；每臂 3×480 tok 固定贪心。异常时自动恢复 0.70 并重启。
set -u
TS=$(date +%Y%m%d_%H%M%S)
CFG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.json
LOG=/home/albus/strata166/data/strata-huihui-ud-iq4_xs.log
OUT=/home/albus/strata166/w863/specminp_$TS.txt
BAK=$CFG.bak_w863smp_$TS
CONT=strata166-407
OKFLAG=/tmp/w863_smp_done
rm -f "$OKFLAG"

set_val() {  # $1 = value
  python3 - "$CFG" "$1" >> "$OUT" 2>&1 <<'PY'
import json, sys
cfg, v = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
a = d['args']
i = a.index('--spec-min-p')
old = a[i+1]
a[i+1] = v
json.dump(d, open(cfg, 'w'), indent=2, ensure_ascii=False)
print('spec-min-p %s -> %s' % (old, v))
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
            "messages": [{"role": "user", "content": "回复一个字：好"}], "max_tokens": 4, "temperature": 0}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r: r.read()
        print("warm %d ok" % i)
    except Exception as ex: print("warm %d FAIL %r" % (i, ex))
PY
}

measure() {
  python3 - "$1" "$2" >> "$OUT" 2>&1 <<'PY'
import json, sys, time, urllib.request
n, mt = int(sys.argv[1]), int(sys.argv[2])
PROMPT = ("下面是一段用于压测解码速度的固定文字，请逐字续写，不要总结、不要换题。"
          "在远程测试台上，我们把显存的每一兆字节都算过一遍：权重按层切分、按需常驻，"
          "专家走缓存，提示走分块，剩下的空间留给 KV。")
for i in range(n):
    body = {"model": "qwen3.8-flash-next-ud-q4_k_xl-abliterated",
            "messages": [{"role": "user", "content": PROMPT}], "max_tokens": mt, "temperature": 0}
    req = urllib.request.Request("http://127.0.0.1:8090/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.loads(r.read())
        print("run %d: wall=%.3fs tokens=%s" % (i, time.time()-t0, d.get("usage",{}).get("completion_tokens")))
    except Exception as ex:
        print("run %d FAIL %r" % (i, ex))
PY
}

keepup() {
  if [ ! -f "$OKFLAG" ]; then
    echo "=== SAFETY restore 0.70 $(date +%H:%M:%S) ===" >> "$OUT"
    set_val 0.70
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
trap 'keepup' EXIT HUP INT TERM

for arm in 0.70 0.40 0.70 0.40; do
  echo "=== ARM spec-min-p=$arm $(date +%H:%M:%S) ===" >> "$OUT"
  set_val "$arm"
  restart_up
  grep -a "spec_min_p=" "$LOG" | tail -1 | grep -o "spec_min_p=[0-9.]*" >> "$OUT"
  warm2
  prev=$(wc -l < "$LOG")
  measure 3 480
  tail -n +$((prev + 1)) "$LOG" | grep -a -E "^strata serve: prompt .* generated" >> "$OUT"
done

echo "=== RESTORE 0.70 $(date +%H:%M:%S) ===" >> "$OUT"
set_val 0.70
restart_up
curl -s --max-time 8 http://127.0.0.1:8090/health >> "$OUT" 2>&1; echo >> "$OUT"
python3 -c "import json;d=json.load(open('$CFG'));a=d['args'];print('final spec-min-p=',a[a.index('--spec-min-p')+1])" >> "$OUT"
touch "$OKFLAG"
echo "DONE $(date +%H:%M:%S)" >> "$OUT"
