#!/bin/bash
# W929 A 臂：k8v4 + STRATA_PREFILL_TIMING=1，拿阶段分解基线
set -u
C="docker exec strata166-407"
CFG=/data/strata-huihui-ud-iq4_xs.json

echo "=== 0. 备份 ==="
$C cp $CFG ${CFG}.bak_w929
$C md5sum $CFG

echo "=== 1. 加 STRATA_PREFILL_TIMING=1（k8v4 不变）==="
$C python3 -c "
import json
p='$CFG'
d=json.load(open(p))
d['env']['STRATA_PREFILL_TIMING']='1'
json.dump(d,open(p,'w'),indent=2,ensure_ascii=False)
print('kv =', d['args'][d['args'].index('--kv')+1])
print('env count =', len(d['env']))
print('timing =', d['env']['STRATA_PREFILL_TIMING'])
"

echo "=== 2. 重启 ==="
docker restart strata166-407
echo "=== 3. 等健康 ==="
for i in $(seq 1 70); do
  s=$(curl -s -m 3 http://127.0.0.1:8090/health 2>/dev/null)
  case "$s" in *'"ok"'*) echo "UP after $((i*5))s"; break;; esac
  sleep 5
done

echo "=== 4. 确认布局（KV 模式 + expert cache）==="
$C sh -c "grep -E 'expert cache [0-9]+ slots|VRAM free with everything' /data/strata-huihui-ud-iq4_xs.log | tail -2"
$C sh -c "tr '\0' ' ' < /proc/\$(pgrep -f 'strata-0.1.55t --serve'|head -1)/cmdline | grep -o '\-\-kv [a-z0-9_]*'"
